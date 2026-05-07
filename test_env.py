import youtube_transcript_api
print(f"Location: {youtube_transcript_api.__file__}")
print(f"Version: {getattr(youtube_transcript_api, '__version__', 'Unknown')}")
from youtube_transcript_api import YouTubeTranscriptApi
print("Methods available:", dir(YouTubeTranscriptApi))
