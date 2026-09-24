"""Seedance routing and request tests; no paid generation requests."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[2] / 'skills/aigc-video-gen/scripts/gen_volc.py'
spec = importlib.util.spec_from_file_location('video_volc', SCRIPT)
volc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(volc)


class TestVolcVideo(unittest.TestCase):
    def args(self, *extra):
        return volc.build_parser().parse_args(['video', '--prompt', 'test', '--output', 'tmp/test.mp4', *extra])

    def test_candidate_order_and_removed_models(self):
        self.assertEqual(volc.volc_candidates(self.args()), [
            'doubao-seedance-2-5-260628', 'doubao-seedance-2-0-fast-260128'])
        for model in ('doubao-seedance-2-0-260128', 'doubao-seedance-2-0-mini-260615'):
            args = self.args()
            args.model = model
            with self.assertRaises(SystemExit):
                volc.volc_candidates(args)

    def test_duration_and_capability_filter(self):
        self.assertEqual(volc.volc_candidates(self.args('--duration', '30')), [volc.VOLC_MODELS['2.5']])
        self.assertEqual(len(volc.volc_candidates(self.args('--duration', '-1'))), 2)
        for value in ('2', '3', '31', '0'):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                volc.volc_candidates(self.args('--duration', value))
        with self.assertRaises(SystemExit):
            volc.volc_candidates(self.args('--duration', '16', '--model', volc.VOLC_MODELS['fast']))

    def test_frame_adaptive_and_reference_roles(self):
        args = self.args('--image', 'asset://first', '--last-frame', 'data:image/png;base64,AA==')
        payload = volc.volc_build_payload(volc.VOLC_MODELS['2.5'], args)
        self.assertEqual(payload['ratio'], 'adaptive')
        self.assertEqual(args.ratio, '9:16')
        self.assertEqual([x.get('role') for x in payload['content'][1:]], ['first_frame', 'last_frame'])
        self.assertEqual(volc.volc_build_payload(volc.VOLC_MODELS['fast'], args)['ratio'], '9:16')
        args = self.args('--ref-image', 'asset://a', '--ref-image', 'asset://b',
                         '--ref-video', 'https://example.com/a.mp4', '--ref-audio', 'https://example.com/a.mp3')
        payload = volc.volc_build_payload(volc.VOLC_MODELS['2.5'], args)
        self.assertEqual([x.get('role') for x in payload['content'][1:]],
                         ['reference_image', 'reference_image', 'reference_video', 'reference_audio'])

    def test_audio_only_and_reference_count(self):
        args = self.args('--ref-audio', 'https://example.com/a.mp3')
        args.prompt = None
        self.assertEqual(volc.volc_candidates(args), [volc.VOLC_MODELS['2.5']])
        self.assertEqual(volc.volc_build_payload(volc.VOLC_MODELS['2.5'], args)['content'][0]['type'], 'audio_url')
        args = self.args()
        args.ref_image = ['asset://a'] * 10
        self.assertEqual(volc.volc_candidates(args), [volc.VOLC_MODELS['2.5']])
        args.ref_image *= 4
        with self.assertRaises(SystemExit):
            volc.volc_candidates(args)

    def test_invalid_combinations_fail_before_submit(self):
        combinations = [('--image', 'asset://a', '--ref-video', 'https://example.com/a.mp4'),
                        ('--last-frame', 'asset://a'),
                        ('--ref-audio', 'https://example.com/a.mp3', '--no-audio'),
                        ('--prev-segment', 'not-read.mp4', '--ref-image', 'asset://a')]
        for extra in combinations:
            with self.subTest(extra=extra), mock.patch.object(volc, 'post_json') as post:
                with self.assertRaises(SystemExit):
                    volc.cmd_video(self.args(*extra))
                post.assert_not_called()
        args = self.args()
        args.prompt = None
        with self.assertRaises(SystemExit):
            volc.validate_inputs(args)

    def test_submit_contract(self):
        with mock.patch.object(volc, 'post_json', return_value={'id': 'test-task'}) as post:
            self.assertEqual(volc.volc_submit(volc.VOLC_MODELS['2.5'], self.args('--resolution', '480p'), 'fake-key'), 'test-task')
        url, body, headers = post.call_args.args
        self.assertEqual(url, 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks')
        self.assertEqual(headers['Authorization'], 'Bearer fake-key')
        self.assertEqual(body['resolution'], '480p')
        self.assertEqual(body['duration'], 8)
        self.assertTrue(body['generate_audio'])

    def test_fallback_uses_only_supported_models(self):
        args = self.args()
        candidates = volc.volc_candidates(args)
        with mock.patch.object(volc, 'volc_submit', side_effect=['task-25', 'task-fast']) as submit, \
             mock.patch.object(volc, 'volc_poll', side_effect=[volc.TaskFailed('not available'), 'https://example.com/out.mp4']), \
             mock.patch('aigc_common.append_decision'):
            result = volc.generate('volcengine', candidates, args, 'fake-key', volc.run_one)
        self.assertEqual(result, 'https://example.com/out.mp4')
        self.assertEqual(args.used_model, volc.VOLC_MODELS['fast'])
        self.assertEqual(args.effective_ratio, '9:16')
        self.assertEqual([call.args[0] for call in submit.call_args_list], candidates)

    def test_poll_success_failure_and_timeout(self):
        with mock.patch.object(volc, 'get_json', return_value={'status': 'succeeded', 'content': {'video_url': 'https://example.com/a.mp4'}}):
            self.assertEqual(volc.volc_poll('test', 'fake'), 'https://example.com/a.mp4')
        with mock.patch.object(volc, 'get_json', return_value={'status': 'failed', 'error': {'code': 'InvalidParameter'}}):
            with self.assertRaises(volc.TaskFailed):
                volc.volc_poll('test', 'fake')
        with mock.patch.object(volc, 'VOLC_TIMEOUT', 0), self.assertRaises(SystemExit):
            volc.volc_poll('test', 'fake')


if __name__ == '__main__':
    unittest.main()
