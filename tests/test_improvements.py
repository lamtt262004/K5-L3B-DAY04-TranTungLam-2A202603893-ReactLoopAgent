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


if __name__ == '__main__':
    unittest.main()
