import streamlit as st
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import cv2
import os
import anthropic
import base64
from pathlib import Path
import re

client = anthropic.Anthropic(
    api_key=st.secrets["api_key"]
)

def get_frames(video_url, num_frames):
    yt = YouTube(video_url)
    video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
    video_file = video.download()
    cap = cv2.VideoCapture(video_file)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = total_frames // (num_frames - 1)
    frames = []
    for i in range(num_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * frame_step)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    cap.release()
    os.remove(video_file)
    return frames

def vision(frames, prompt):
    image_data_list = []
    for frame in frames:
        _, encoded_frame = cv2.imencode(".jpg", frame)
        image_data_base64 = base64.b64encode(encoded_frame).decode("utf-8")
        image_data_list.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_data_base64,
            }
        })
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": image_data_list + [{"type": "text", "text": prompt}],
        }]
    )
    response_text = message.content[0].text
    return response_text

def get_transcript(url):
    match = re.search(r'v=([^&#]+)', url)
    if match:
        video_id = match.group(1)
    else:
        raise ValueError("Invalid YouTube link")
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return ' '.join([entry['text'] for entry in transcript])

def save_file(md):
    filename = "output.md"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(md)

def formatting(text):
    new_text_lines = []
    lines = text.split('\n')

    for line in lines:
        if not line.strip().startswith('```') and not line.strip().startswith('´´´') and not line.strip().startswith('    '):
            new_text_lines.append(line)

    new_text = '\n'.join(new_text_lines)
    return new_text


title = st.empty()
url = st.empty()
language = st.empty()
slider = st.empty()
button = st.empty()

def main():
    title.title("Lucius")
    video_url = url.text_input("Enter YouTube video URL:")
    if language.selectbox("Choose your language:", ["English", "German"]) == "German":
        system_prompt = "Sie sind eine KI, die Markdown-Code für Videotranskripte in deutscher Sprache erstellt. Erstellen Sie einen Markdown-Code für das vorherige Transkript. Er sollte gut strukturiert und leicht zu lesen sein. Schreiben Sie nur den Code. Verwende Funktionen wie Tabellenüberschriften und Zwischenüberschriften. Wenn ein Abschnitt für Sie wichtig ist, zitieren Sie ihn, aber geben Sie keinen Autor an. Geben Sie die Quelle am Ende an. Verwenden Sie Tabellen für Vergleiche zwischen verschiedenen Dingen. Stellen Sie alles gut dar. Seien Sie neutral und geben Sie das Video gut wieder. Alle Informationen sollten wiedergegeben werden. Wenn das Video Programmiercode enthält, schreibe ihn in einen Codeblock sollte er nicht in den fotos seien, interpretieren sie das was sie aus dem transcript wissen.. Du bekommst auch Videoframes. Sie können dir helfen, den Stil zu beschreiben oder Dinge wie Code oder Untertitel zu transkribieren."
    else:
        system_prompt = "You are an AI that creates Markdown code for video transcripts. Create a Markdown code for the previous transcript. It should be well structured and easy to read. Write only the code. Use features such as table headings and subheadings. If a section is important to you, cite it, but do not include an author. Cite the source at the end. Use tables for comparisons between different things. Present everything well. Be neutral and reproduce the video well. All information should be reproduced. If the video contains programming code, write it in a code block. You also get vidio frames. they scould help you to describe the style or to transcribe things like code or subtitles"

    num_frames = slider.slider("Number of frames", min_value=2, max_value=20, value=2)

    if button.button("Generate Transcript"):
        with st.spinner("Processing..."):
            transcript = get_transcript(video_url)
            video_frames = get_frames(video_url, num_frames)
            prompt = f"{system_prompt}, Transcript: {transcript}, Video link: {video_url}"
            md = vision(video_frames, prompt)
            save_file(formatting(md))
            st.markdown(md)
            title.empty()
            url.empty()
            slider.empty()
            button.empty()
            language.empty()

if __name__ == "__main__":
    main()
