"""Run: python3 -m unittest discover -s test/skills -p test_voice_customization.py"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'skills/awk-tts/scripts'))
import tts
import voice_customization as voice
import volc_voice


class VoiceCustomizationTests(unittest.TestCase):
    def test_default_routing_preserves_tts_priority(self):
        both = {'VOLC_TTS_APP_ID': 'app', 'VOLC_TTS_ACCESS_KEY': 'access',
                'WORKSPACE_ID': 'workspace', 'MODELSTUDIO_API_KEY': 'key', 'AWK_API_KEY': 'agent'}
        with mock.patch.dict(os.environ, both, clear=True):
            self.assertEqual(voice.route(), 'volc')
            self.assertEqual(voice.route('workspace')[3], 'workspace')
            self.assertEqual(voice.route('agent-plan')[3], 'agent-plan')
        with mock.patch.dict(os.environ, {k: v for k, v in both.items() if not k.startswith('VOLC_')}, clear=True):
            self.assertEqual(voice.route()[3], 'workspace')
        with mock.patch.dict(os.environ, {'AWK_API_KEY': 'agent'}, clear=True):
            self.assertEqual(voice.route()[3], 'agent-plan')

    def test_volc_voice_payload_status_and_profile_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            args = argparse.Namespace(command='voice-design', speaker_id='S_test_slot',
                                      target_model=None, language='zh', description='自然温暖的成年男声',
                                      preview_text='今天我们先讲这张图。', out_dir=folder, wait=0)
            with mock.patch.dict(os.environ, {'VOLC_TTS_APP_ID': 'app', 'VOLC_TTS_ACCESS_KEY': 'access'}, clear=True):
                with mock.patch.object(volc_voice, 'call', return_value={
                    'speaker_id': 'S_test_slot', 'status': 2,
                    'speaker_status': [{'model_type': 5}],
                }) as api:
                    profile_path, profile = volc_voice.create(args)
                self.assertEqual(api.call_args.args[0], '/tts/voice_design')
                self.assertEqual(api.call_args.args[1]['prompt']['text_prompt'], args.description)
                self.assertEqual(profile['model_type'], 5)
                self.assertEqual(profile['status'], 'OK')
                self.assertEqual(voice.load_profile(profile_path)[0], 'volc')
                payload_args = argparse.Namespace(format='wav', sample_rate=None, speech_rate=None,
                                                 loudness_rate=None, enable_subtitle=False,
                                                 voice='S_test_slot', voice_model_type=profile['model_type'],
                                                 context_text=None)
                additions = json.loads(tts.build_payload(payload_args, '测试')['req_params']['additions'])
                self.assertEqual(additions['model_type'], 5)
            with mock.patch.dict(os.environ, {'VOLC_TTS_APP_ID': 'different', 'VOLC_TTS_ACCESS_KEY': 'access'}, clear=True):
                with self.assertRaisesRegex(ValueError, 'APP'):
                    voice.load_profile(profile_path)

    def test_bailian_profile_binds_workspace_and_model(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'voice.json'
            profile = {'provider': 'bailian-workspace',
                       'base_url': 'https://work.cn-beijing.maas.aliyuncs.com/api/v1',
                       'target_model': 'qwen-audio-3.0-tts-plus', 'voice_id': 'custom_voice', 'status': 'OK'}
            path.write_text(json.dumps(profile))
            with mock.patch.dict(os.environ, {'WORKSPACE_ID': 'work', 'MODELSTUDIO_API_KEY': 'key'}, clear=True):
                selected, actual = voice.load_profile(path)
                self.assertEqual(selected[3], 'workspace')
                self.assertEqual(actual['voice_id'], 'custom_voice')
            with mock.patch.dict(os.environ, {'WORKSPACE_ID': 'other', 'MODELSTUDIO_API_KEY': 'key'}, clear=True):
                with self.assertRaisesRegex(ValueError, '业务空间'):
                    voice.load_profile(path)

    def test_volc_clone_payload_uses_sample_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            sample = Path(temp)/'sample.wav'
            sample.write_bytes(b'fixture')
            args = argparse.Namespace(command='voice-clone', speaker_id='S_test_slot',
                                      target_model=None, language='zh', preview_text='试听文本')
            with mock.patch.dict(os.environ, {}, clear=True):
                body = volc_voice.build_payload(args, sample)
            self.assertEqual(body['audio']['format'], 'wav')
            self.assertEqual(body['audio']['data'], 'Zml4dHVyZQ==')
            self.assertEqual(body['extra_params']['demo_text'], '试听文本')


if __name__ == '__main__':
    unittest.main()
