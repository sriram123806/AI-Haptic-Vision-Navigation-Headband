// AUDIO MAPPING LAYER: command id -> uploaded ElevenLabs MP3 in ./audio/ (original filenames).
const AUDIO_DIR = "audio/";
const AUDIO_MAP = {
  move_left:         "ElevenLabs_audio_elevenlabs-v4_Move_left__2026-10-05T18_10_54.mp3",
  move_right:        "ElevenLabs_audio_elevenlabs-v4_Move_right__2026-10-05T18_10_59.mp3",
  move_straight:     "ElevenLabs_audio_elevenlabs-v4_Move_straight__2026-10-05T18_11_01.mp3",
  move_backward:     "ElevenLabs_audio_elevenlabs-v4_Move_backward__2026-10-05T18_11_06.mp3",
  stop:              "ElevenLabs_audio_elevenlabs-v4__firm__Stop__2026-10-05T18_11_06.mp3",
  wait_for_a_while:  "ElevenLabs_audio_elevenlabs-v4_Wait_for_a_whil_2026-10-05T18_11_12.mp3",
  start_walking:     "ElevenLabs_audio_elevenlabs-v4__firm__Start_wa_2026-10-05T18_19_04.mp3",
  obstacle_detected: "ElevenLabs_audio_elevenlabs-v4__firm__Obstacle_2026-10-05T18_11_17.mp3",
  system_ready:      "ElevenLabs_audio_elevenlabs-v4_System_ready__2026-10-05T18_11_17.mp3",
  object_detected:   "ElevenLabs_audio_elevenlabs-v4_Object_detected_2026-10-05T18_11_24.mp3",
  slow_down:         "ElevenLabs_audio_elevenlabs-v4__firm__Slow_dow_2026-10-05T18_19_05.mp3"
};
const AUDIO_ALIAS = { wait: "wait_for_a_while" };   // accepted alternative command names
