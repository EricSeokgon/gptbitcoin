from youtube_transcript_api import YouTubeTranscriptApi


# 자막 데이터 가져오기
transcript = YouTubeTranscriptApi.get_transcript("TWINrTppUl4")


# 텍스트만 추출하여 출력
for entry in transcript:
    print(entry['text'])


# 또는 한 번에 모든 텍스트를 하나의 문자열로 만들고 싶다면:
all_text = ' '.join([entry['text'] for entry in transcript])
print(all_text)
