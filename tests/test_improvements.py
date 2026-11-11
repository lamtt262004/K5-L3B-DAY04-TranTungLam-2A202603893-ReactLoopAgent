"""Tests cho cải tiến Bài 4: theo dõi incident liên quan."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final

H02 = 'https://stspg.io/7pwv28hvkmz8'      # h02n9572mx9y, update dẫn tới xr3myzj7ms51
XR3 = 'https://stspg.io/pjgptg3cfc6n'


class ReferenceFollowTests(unittest.TestCase):
    def test_unread_related_incident_triggers_one_nudge(self):
        fake = FakeProvider([
            tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"h02n9572mx9y"}'),
            final('Đã resolved. ' + H02),
            tool_call('2', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
            final('Đã resolved. ' + H02 + ' ' + XR3)])
        result = run_agent('Điều tra h02n9572mx9y', fake, StatusTools(), max_steps=6)
        self.assertEqual(result['status'], 'completed')
        events = [x for x in result['trace'] if x['event'] == 'validation_unfollowed_reference']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['unread'][0]['incident_id'], 'xr3myzj7ms51')
        self.assertIn('xr3myzj7ms51', fake.histories[2][-1]['content'])

    def test_nudge_is_not_repeated_when_model_declines(self):
        fake = FakeProvider([
            tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"h02n9572mx9y"}'),
            final('Chưa đọc incident liên quan. ' + H02),
            final('Chưa đọc incident liên quan xr3myzj7ms51. ' + H02)])
        result = run_agent('x', fake, StatusTools(), max_steps=6)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(sum(x['event'] == 'validation_unfollowed_reference' for x in result['trace']), 1)

    def test_no_reference_no_nudge(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
                             final('Resolved. ' + XR3)])
        result = run_agent('x', fake, StatusTools())
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(x['event'] == 'validation_unfollowed_reference' for x in result['trace']))

    @patch.dict('os.environ', {'AGENT_BASELINE': '1'})
    def test_baseline_mode_disables_improvements(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"h02n9572mx9y"}'),
                             final('Không có URL')])
        result = run_agent('x', fake, StatusTools())
        self.assertEqual(result['status'], 'completed')
        self.assertNotIn('Quy tắc bổ sung', fake.histories[0][0]['content'])


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'evals'))
from scenarios import ScenarioTools
from agent import MARKER_TOKEN


def _planted_marker():
    """Lấy marker từ scenario thay vì hard-code."""
    notice = ScenarioTools('status_injection').execute('get_status', {'provider': 'github'})['external_notice']
    return MARKER_TOKEN.findall(notice)[0]


class InjectionTests(unittest.TestCase):
    def test_injected_text_is_hidden_from_model(self):
        marker = _planted_marker()
        fake = FakeProvider([tool_call('1', 'get_status', '{"provider":"github"}'), final('GitHub ổn.')])
        result = run_agent('x', fake, ScenarioTools('status_injection'))
        self.assertEqual(result['status'], 'completed')
        tool_msg = fake.histories[1][-1]
        self.assertEqual(tool_msg['role'], 'tool')
        self.assertNotIn(marker, tool_msg['content'])
        self.assertTrue(any(x['event'] == 'tool_injection_hidden' for x in result['trace']))

    def test_answer_echoing_marker_must_be_rewritten(self):
        marker = _planted_marker()
        fake = FakeProvider([tool_call('1', 'get_status', '{"provider":"github"}'),
                             final(f'Có notice giả: {marker}'),
                             final('Có một notice đáng ngờ, đã bỏ qua.')])
        result = run_agent('x', fake, ScenarioTools('status_injection'))
        self.assertEqual(result['status'], 'completed')
        self.assertNotIn(marker, result['answer'])
        self.assertEqual(sum(x['event'] == 'validation_injection_echo' for x in result['trace']), 1)

    def test_normal_fixture_is_not_altered(self):
        fake = FakeProvider([tool_call('1', 'get_status', '{"provider":"github"}'), final('ok')])
        result = run_agent('x', fake, StatusTools())
        self.assertFalse(any(x['event'] == 'tool_injection_hidden' for x in result['trace']))


if __name__ == '__main__':
    unittest.main()
