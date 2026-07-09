from Simpler_Kokoro import SimplerKokoro
import os

def test_simpler():
    print("Initializing SimplerKokoro...")
    try:
        sk = SimplerKokoro()
        print("Initialization successful.")
        
        text = "Hello, this is a test for subtitle generation."
        wav_path = "test_simpler.wav"
        srt_path = "test_simpler.srt"
        
        print(f"Generating speech and subtitles for: {text}")
        sk.generate(
            text=text,
            voice="af_heart",
            output_path=wav_path,
            write_subtitles=True,
            subtitles_path=srt_path
        )
        
        if os.path.exists(wav_path):
            print(f"SUCCESS: Audio file created at {wav_path}")
        else:
            print("FAILURE: Audio file NOT created.")
            
        if os.path.exists(srt_path):
            print(f"SUCCESS: Subtitle file created at {srt_path}")
            with open(srt_path, 'r') as f:
                print("SRT Content preview:")
                print(f.read())
        else:
            print("FAILURE: Subtitle file NOT created.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_simpler()
