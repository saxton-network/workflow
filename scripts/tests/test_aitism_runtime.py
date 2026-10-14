"""Adversarial runtime tests: assert blocked progression, not only error text."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aitism_runtime.cli import main
from aitism_runtime.contracts import Rejected, canonical, decode, digest, validate_plan
from aitism_runtime.git_state import GitObserver
from aitism_runtime.planner import propose
from aitism_runtime.providers import MockProvider, ProviderBus
from aitism_runtime.runtime import Runtime
from aitism_runtime.store import Store


class ObservedGit:
    def __init__(self):
        self.sha = "a"*40
        self.branch = "experimental/features"
        self.unknown = False

    def check(self, plan):
        if self.unknown or (self.sha, self.branch) != (plan["source_sha"], plan["source_branch"]):
            raise Rejected("Git unknown/divergent")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "runtime.sqlite"
        self.store = Store(self.path)
        self.git = ObservedGit()
        self.now = 100
        self.runtime = Runtime(self.store, self.git, clock=lambda: self.now)
        self.plan = propose("Build a simulated feature", self.git.sha, "test")

    def ready(self, plan=None):
        plan = plan or self.plan
        wid = plan["workflow_id"]
        state = self.runtime.create(plan, actor="human")
        for role, task in (("builder", "build"), ("reviewer", "review"), ("validator", "validate")):
            self.runtime.enroll(wid, role, role, task, actor="human")
        self.runtime.approve(wid, state["plan_hash"], "operator-approved-simulation", actor="human")
        return wid

    def rejected_without_write(self, fn, wid="test"):
        before = self.store.events(wid)
        with self.assertRaises(Rejected):
            fn()
        self.assertEqual(before, self.store.events(wid))

    def test_end_to_end_durable_separate_review_and_idempotence(self):
        self.ready()
        self.assertEqual(self.runtime.inspect("test")["eligible_tasks"], ["build"])
        build = self.runtime.advance("test", actor="coordinator")["state"]
        self.assertEqual(build["tasks"]["review"]["status"], "pending")
        self.assertEqual(self.runtime.inspect("test")["eligible_tasks"], ["review"])
        review = self.runtime.advance("test", actor="coordinator")["state"]
        self.assertEqual(review["tasks"]["review"]["status"], "passed")
        self.assertNotEqual(review["tasks"]["build"]["agent"], review["tasks"]["review"]["agent"])
        self.runtime.advance("test", actor="coordinator")
        reopened = Runtime(Store(self.path), self.git, clock=lambda: self.now)
        final = reopened.inspect("test")
        self.assertEqual(final["state"]["status"], "completed")
        self.assertFalse(final["deployment_authority"])
        self.assertEqual(final["eligible_tasks"], [])
        self.assertEqual(final["state"]["usage"], {"input_tokens":30,"output_tokens":15,"cost_microusd":0})
        self.assertEqual(final["state"]["reserved_tokens"], 45)
        before = self.store.events("test")
        reopened.advance("test", actor="coordinator")
        task = final["state"]["tasks"]["validate"]
        reopened.finish("test", "validate", task["history"][-1]["lease"], task["result"], actor="coordinator")
        self.assertEqual(before, self.store.events("test"))
        self.assertEqual(len(before), 11)

    def test_draft_and_wrong_approval_cannot_dispatch(self):
        state = self.runtime.create(self.plan, actor="human")
        self.runtime.enroll("test", "builder", "builder", "build", actor="human")
        for actor, checksum, reference in (("builder",state["plan_hash"],"ref"),
                                           ("human","b"*64,"ref"), ("human",state["plan_hash"]," ")):
            self.rejected_without_write(lambda: self.runtime.approve("test",checksum,reference,actor=actor))
        self.rejected_without_write(lambda: self.runtime.claim("test","build",actor="coordinator"))
        self.assertEqual(self.runtime.inspect("test")["eligible_tasks"], [])

    def test_foreign_workflow_approval_rejected(self):
        self.ready()
        other = propose("Other objective",self.git.sha,"other")
        self.runtime.create(other,actor="human")
        self.rejected_without_write(lambda: self.runtime.approve("other",digest(self.plan),"ref",actor="human"),wid="other")

    def test_dependencies_cannot_be_skipped(self):
        self.ready()
        for task in ("review", "validate"):
            self.rejected_without_write(lambda: self.runtime.claim("test",task,actor="coordinator"))

    def test_agents_cannot_delegate_expand_permissions_or_accept_results(self):
        self.ready()
        request = self.runtime.claim("test","build",actor="coordinator")
        result = MockProvider().dispatch(request,timeout_seconds=30)
        denied = [lambda: self.runtime.enroll("test","child","reviewer","review",parent="builder",actor="builder"),
                  lambda: self.runtime.claim("test","review",actor="builder"),
                  lambda: self.runtime.finish("test","build",request["lease"],result,actor="builder"),
                  lambda: self.runtime.cancel("test",actor="builder"),
                  lambda: self.runtime.recover("test",actor="builder")]
        for operation in denied:
            self.rejected_without_write(operation)
        self.assertEqual(set(self.store.read("test")["agents"]), {"builder","reviewer","validator"})

    def test_invalid_enrollment_roles_reserved_identity_and_parent(self):
        self.runtime.create(self.plan,actor="human")
        for agent,role,parent in (("human","builder",None),("builder","reviewer",None),
                                  ("builder","builder","unknown")):
            self.rejected_without_write(lambda: self.runtime.enroll("test",agent,role,"build",actor="human",parent=parent))

    def test_human_lineage_grants_only_declared_child_role(self):
        self.runtime.create(self.plan,actor="human")
        self.runtime.enroll("test","builder","builder","build",actor="human")
        state = self.runtime.enroll("test","reviewer","reviewer","review",actor="human",parent="builder")
        self.assertEqual(state["agents"]["reviewer"]["parent"],"builder")
        self.assertEqual(state["agents"]["reviewer"]["role"],"reviewer")

    def test_crash_checkpoint_restart_recovery_and_explicit_retry(self):
        self.ready()
        request = self.runtime.claim("test","build",actor="coordinator")
        self.runtime.checkpoint("test","build",request["lease"],{"progress":"mock prepared"},actor="builder")
        self.assertIsNone(self.store.read("test")["usage"]["input_tokens"])
        self.now = 130
        restarted = Runtime(Store(self.path),self.git,clock=lambda:self.now)
        failed = restarted.recover("test",actor="coordinator")
        self.assertEqual(failed["status"],"failed")
        self.assertEqual(failed["tasks"]["build"]["checkpoint"]["data"],{"progress":"mock prepared"})
        self.assertEqual(restarted.inspect("test")["eligible_tasks"],[])
        old_result = MockProvider().dispatch(request,timeout_seconds=30)
        self.rejected_without_write(lambda: restarted.finish("test","build",request["lease"],old_result,actor="coordinator"))
        restarted.retry("test","build",actor="coordinator")
        new_request = restarted.claim("test","build",actor="coordinator")
        self.assertNotEqual(new_request["lease"],request["lease"])
        self.rejected_without_write(lambda: restarted.finish("test","build",request["lease"],old_result,actor="coordinator"))
        restarted.finish("test","build",new_request["lease"],MockProvider().dispatch(new_request,timeout_seconds=30),actor="coordinator")
        restarted.advance("test",actor="coordinator")
        done = restarted.advance("test",actor="coordinator")["state"]
        self.assertEqual(done["status"],"completed")
        self.assertEqual([a["status"] for a in done["tasks"]["build"]["history"]],["failed","complete"])
        self.assertIsNone(done["usage"]["input_tokens"])
        self.assertEqual(done["reserved_tokens"],60)

    def test_heartbeat_owner_and_expiry_fence(self):
        self.ready()
        request=self.runtime.claim("test","build",actor="coordinator")
        self.rejected_without_write(lambda:self.runtime.heartbeat("test","build",request["lease"],actor="reviewer"))
        self.now=110
        self.runtime.heartbeat("test","build",request["lease"],actor="builder")
        self.now=130
        self.assertEqual(self.runtime.recover("test",actor="coordinator")["status"],"running")
        self.now=140
        self.rejected_without_write(lambda:self.runtime.heartbeat("test","build",request["lease"],actor="builder"))
        self.runtime.recover("test",actor="coordinator")
        self.assertEqual(self.store.read("test")["agents"]["builder"]["state"],"stopped")

    def test_cancel_fences_late_result_and_prevents_retry(self):
        self.ready()
        request=self.runtime.claim("test","build",actor="coordinator")
        result=MockProvider().dispatch(request,timeout_seconds=30)
        self.runtime.cancel("test",actor="human")
        self.rejected_without_write(lambda:self.runtime.finish("test","build",request["lease"],result,actor="coordinator"))
        self.rejected_without_write(lambda:self.runtime.retry("test","build",actor="coordinator"))
        self.assertEqual(self.runtime.inspect("test")["eligible_tasks"],[])
        self.assertEqual(self.store.read("test")["tasks"]["build"]["history"][0]["status"],"cancelled")

    def test_provider_bad_evidence_fails_without_successors(self):
        faults = (lambda r:r.update(verdict="FAIL"), lambda r:r.update(verdict="UNKNOWN"),
                  lambda r:r.update(artifact_hash="0"*64),lambda r:r.update(source_sha="b"*40),
                  lambda r:r.update(subject_hash="c"*64),lambda r:r.update(model="wrong-model"),
                  lambda r:r.update(workflow_id="foreign"),lambda r:r.update(usage={"input_tokens":None,"output_tokens":None,"cost_microusd":None}),
                  lambda r:r.update(unexpected="authority"))
        for index, fault in enumerate(faults):
            with self.subTest(index=index):
                plan=propose("fault",self.git.sha,f"fault{index}")
                wid=self.ready(plan)
                request=self.runtime.claim(wid,"build",actor="coordinator")
                result=MockProvider().dispatch(request,timeout_seconds=30)
                fault(result)
                failed=self.runtime.finish(wid,"build",request["lease"],result,actor="coordinator")
                self.assertEqual(failed["status"],"failed")
                self.assertEqual(self.runtime.inspect(wid)["eligible_tasks"],[])
                self.assertEqual(failed["tasks"]["review"]["status"],"pending")
                self.assertTrue(failed["tasks"]["build"]["history"][-1]["reason"])

    def test_provider_exception_timeout_sanitization_and_no_retry(self):
        for index, error in enumerate((RuntimeError("secret-value"),TimeoutError("secret-value"))):
            plan=propose("provider failure",self.git.sha,f"provider{index}")
            wid=self.ready(plan)
            with patch.object(MockProvider,"dispatch",side_effect=error) as dispatch:
                view=self.runtime.advance(wid,actor="coordinator")
                self.runtime.advance(wid,actor="coordinator")
                self.assertEqual(dispatch.call_count,1)
            self.assertEqual(view["state"]["status"],"failed")
            self.assertNotIn("secret-value",canonical(self.store.events(wid)))
            self.assertIsNone(view["state"]["usage"]["cost_microusd"])

    def test_provider_unavailable_prevents_claim(self):
        self.ready()
        info=MockProvider().describe()
        info['available']=False
        with patch.object(MockProvider,'describe',return_value=info):
            self.rejected_without_write(lambda:self.runtime.claim("test","build",actor="coordinator"))
        self.assertEqual(self.store.read("test")["tasks"]["build"]["attempt"],0)

    def test_review_binds_exact_build_artifact(self):
        self.ready()
        self.runtime.advance("test",actor="coordinator")
        request=self.runtime.claim("test","review",actor="coordinator")
        result=MockProvider().dispatch(request,timeout_seconds=30)
        result['subject_hash']='0'*64
        failed=self.runtime.finish("test","review",request['lease'],result,actor="coordinator")
        self.assertEqual(failed['tasks']['review']['status'],'failed')
        self.rejected_without_write(lambda:self.runtime.claim("test","validate",actor="coordinator"))

    def test_conflicting_completed_result_is_rejected(self):
        self.ready()
        request=self.runtime.claim("test","build",actor="coordinator")
        result=MockProvider().dispatch(request,timeout_seconds=30)
        self.runtime.finish("test","build",request['lease'],result,actor="coordinator")
        result['artifact']['objective']='changed'
        self.rejected_without_write(lambda:self.runtime.finish("test","build",request['lease'],result,actor="coordinator"))

    def test_frozen_budget_and_retry_limit(self):
        plan=deepcopy(self.plan)
        plan['estimates']['max_tokens']=15
        self.ready(plan)
        self.runtime.advance("test",actor="coordinator")
        self.rejected_without_write(lambda:self.runtime.claim("test","review",actor="coordinator"))
        plan=propose('retry limit',self.git.sha,'limit')
        plan['estimates']['max_attempts']=1
        self.ready(plan)
        request=self.runtime.claim('limit','build',actor='coordinator')
        self.runtime.finish('limit','build',request['lease'],None,error='mock failure',actor='coordinator')
        self.rejected_without_write(lambda:self.runtime.retry('limit','build',actor='coordinator'),wid='limit')

    def test_git_mismatch_or_unknown_blocks_claim_and_finish(self):
        self.ready()
        self.git.unknown=True
        self.rejected_without_write(lambda:self.runtime.claim('test','build',actor='coordinator'))
        self.git.unknown=False
        request=self.runtime.claim('test','build',actor='coordinator')
        result=MockProvider().dispatch(request,timeout_seconds=30)
        self.git.sha='b'*40
        self.rejected_without_write(lambda:self.runtime.finish('test','build',request['lease'],result,actor='coordinator'))
        self.assertEqual(self.store.read('test')['tasks']['build']['status'],'running')

    def test_clock_regression_blocks_mutation(self):
        self.ready()
        self.now=99
        self.rejected_without_write(lambda:self.runtime.claim('test','build',actor='coordinator'))

    def test_resource_ownership_across_workflows(self):
        self.ready()
        other=propose('other',self.git.sha,'other')
        other['tasks'][0]['worktree']=self.plan['tasks'][0]['worktree']
        self.ready(other)
        self.runtime.claim('test','build',actor='coordinator')
        self.rejected_without_write(lambda:self.runtime.claim('other','build',actor='coordinator'),wid='other')
        self.assertEqual(self.store.read('other')['tasks']['build']['attempt'],0)

    def test_concurrent_process_claim_only_one_dispatch_lease(self):
        self.ready()
        script = '''from pathlib import Path
from aitism_runtime.store import Store
from aitism_runtime.runtime import Runtime
from aitism_runtime.contracts import Rejected
import sys
class Git:
 def check(self,plan): pass
try:
 r=Runtime(Store(Path(sys.argv[1])),Git(),clock=lambda:100)
 print(r.claim("test","build",actor="coordinator")["lease"])
except Rejected:
 sys.exit(2)
'''
        def run():
            return subprocess.run([sys.executable,'-c',script,str(self.path)],cwd=ROOT,capture_output=True,text=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outputs=list(pool.map(lambda _:run(),range(2)))
        self.assertEqual(sorted(r.returncode for r in outputs),[0,2])
        self.assertEqual(len(self.store.read('test')['tasks']['build']['history']),1)
        self.assertEqual(len(self.store.events('test')),6)

    def test_interrupted_transaction_leaves_no_partial_checkpoint(self):
        self.ready()
        before=self.store.read('test')
        with self.assertRaises(RuntimeError):
            with self.store.transaction() as db:
                db.execute('UPDATE workflows SET state=? WHERE id=?',('{}','test'))
                raise RuntimeError('process interrupted before commit')
        self.assertEqual(self.store.read('test'),before)

    def test_abrupt_process_exit_rolls_back_state_and_event_append(self):
        self.ready()
        before=self.store.events('test')
        script='''import os, sqlite3, sys
db=sqlite3.connect(sys.argv[1],isolation_level=None)
db.execute("BEGIN IMMEDIATE")
db.execute("UPDATE workflows SET state='{}' WHERE id='test'")
db.execute("INSERT INTO events VALUES ('test',6,'{}','bad')")
os._exit(23)
'''
        output=subprocess.run([sys.executable,'-c',script,str(self.path)],capture_output=True)
        self.assertEqual(output.returncode,23)
        self.assertEqual(self.store.events('test'),before)

    def test_sql_journal_is_append_only(self):
        self.ready()
        for sql in ('DELETE FROM events','UPDATE events SET hash="bad"'):
            with self.assertRaises(sqlite3.IntegrityError):
                with self.store.transaction() as db:
                    db.execute(sql)
        self.assertEqual(len(self.store.events('test')),5)

    def corrupt_projection(self, change):
        with sqlite3.connect(self.path) as db:
            state=decode(db.execute('SELECT state FROM workflows WHERE id="test"').fetchone()[0])
            change(state)
            db.execute('UPDATE workflows SET state=? WHERE id="test"',(canonical(state),))

    def test_corrupted_projection_checkpoint_and_unknown_status_block_all_processing(self):
        self.ready()
        request=self.runtime.claim('test','build',actor='coordinator')
        self.runtime.checkpoint('test','build',request['lease'],{'step':1},actor='builder')
        original=self.store.read('test')
        for change in (lambda s:s['tasks']['build']['checkpoint']['data'].update(step=2),
                       lambda s:s.update(status='unknown'),lambda s:s['approval'].update(plan_hash='b'*64)):
            self.corrupt_projection(change)
            for operation in (lambda:self.runtime.inspect('test'),lambda:self.runtime.recover('test',actor='coordinator'),
                              lambda:self.runtime.advance('test',actor='coordinator')):
                with self.assertRaises(Rejected):operation()
            with sqlite3.connect(self.path) as db:
                db.execute('UPDATE workflows SET state=? WHERE id="test"',(canonical(original),))

    def test_journal_damage_fails_closed(self):
        self.ready()
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TRIGGER events_no_update')  # Fault injection only; production never does this.
            db.execute('UPDATE events SET hash=? WHERE sequence=1',('0'*64,))
        for operation in (lambda:self.store.events('test'),lambda:self.runtime.claim('test','build',actor='coordinator')):
            with self.assertRaises(Rejected):operation()

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for raw in ('{"schema_version":1,"schema_version":1}','{"value":NaN}','{"value":Infinity}'):
            with self.assertRaises(Rejected):decode(raw)

    def test_plan_graph_version_alias_and_live_kind_rejected(self):
        cases=[]
        for change in (lambda p:p.update(schema_version=2),lambda p:p['tasks'][0].update(kind='live_deployment'),
                       lambda p:p['tasks'][0].update(depends_on=['review']),lambda p:p['tasks'][1].update(subject='missing'),
                       lambda p:p['tasks'][2].update(depends_on=['build']),
                       lambda p:p['tasks'][1].update(branch=p['tasks'][0]['branch']),
                       lambda p:p['tasks'][0].update(worktree='sim/test/../build'),
                       lambda p:p.update(delegated_permissions=['shell'])):
            plan=deepcopy(self.plan); change(plan); cases.append(plan)
        for plan in cases:
            with self.assertRaises(Rejected):validate_plan(plan)
        self.assertFalse(self.path.with_name('external-call').exists())

    def test_store_version_rejected(self):
        with sqlite3.connect(self.path) as db:db.execute('PRAGMA user_version=99')
        with self.assertRaises(Rejected):Store(self.path)

    def test_cli_bad_input_has_structured_blocked_verdict(self):
        plan_path=Path(self.tmp.name)/'bad.json'
        plan_path.write_text('{"schema_version":1,"schema_version":1}')
        with patch('sys.stderr',new_callable=io.StringIO) as stderr:
            code=main(['--store',str(self.path),'create',str(plan_path),'--actor','human'])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(stderr.getvalue())['verdict'],'BLOCKED')


class GitObservationTests(unittest.TestCase):
    def test_actual_checkout_branch_and_exact_sha(self):
        observer=GitObserver(ROOT)
        sha,branch=observer.observe()
        self.assertEqual(branch,'experimental/features')
        observer.check(propose('observe',sha,'observe'))
        with self.assertRaises(Rejected):observer.check(propose('stale','0'*40,'observe'))

    def test_missing_checkout_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(Rejected):GitObserver(Path(directory)).observe()

    def test_accidental_git_environment_cannot_redirect_observation(self):
        expected=GitObserver(ROOT).observe()
        with patch.dict('os.environ',{'GIT_DIR':'/missing','GIT_WORK_TREE':'/missing'}):
            self.assertEqual(GitObserver(ROOT).observe(),expected)

    def test_mock_dispatch_uses_no_subprocess_or_network(self):
        plan=propose('no external calls','a'*40,'mock')
        request={'schema_version':1,'workflow_id':'mock','task_id':'build','attempt':1,
                 'lease':'b'*64,'plan_hash':digest(plan),'source_sha':'a'*40,
                 'subject_hash':None,'objective':'no external calls','kind':'build','model':'mock-builder-v1'}
        with patch('subprocess.run',side_effect=AssertionError('shell denied')),patch('socket.socket',side_effect=AssertionError('network denied')):
            self.assertEqual(MockProvider().dispatch(request,timeout_seconds=1)['verdict'],'PASS')
            self.assertEqual(MockProvider().dispatch(request,timeout_seconds=1),MockProvider().dispatch(request,timeout_seconds=1))


if __name__ == '__main__':
    unittest.main()
