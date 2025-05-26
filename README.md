# Audio Transcription App

A Streamlit-based application that transcribes audio files using OpenAI's Whisper API and generates intelligent meeting summaries.

## ✨ Features

- **Multi-format Audio Support**: MP3, MP4, WAV, M4A, WebM, and more
- **Large File Handling**: Automatic chunking for files longer than 10 minutes
- **Smart Transcription**: Context-aware processing with meeting descriptions
- **Multi-language Support**: Italian, English, Spanish, French, German, and auto-detection
- **Interactive Editing**: Edit transcripts before generating summaries
- **AI-Powered Summaries**: Extract key insights and meeting notes
- **Streaming Output**: Real-time transcription for shorter files

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd transcribe-audio
```

2. Install dependencies using uv (recommended):
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

4. Run the application:
```bash
streamlit run app_improved.py
```

## 📖 Usage

1. **Upload Audio**: Choose an audio file (max 25MB per OpenAI's limit)
2. **Describe Meeting** (Optional): Add context to improve transcription accuracy
3. **Select Language**: Choose the audio language or use auto-detection
4. **Transcribe**: Click the transcribe button and wait for processing
5. **Edit Transcript**: Make any necessary corrections
6. **Generate Summary**: Create structured meeting notes and key insights

## 🔧 Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Audio Processing

- **Max Duration per Chunk**: 10 minutes (600 seconds)
- **Supported Formats**: MP3, MP4, MPEG, MPGA, M4A, WAV, WebM
- **File Size Limit**: 25MB (OpenAI API limitation)

## 🏗️ Architecture

```
transcribe-audio/
├── app.py              # Main Streamlit application
├── prompts.py          # AI prompts for summarization
├── pyproject.toml      # Project configuration
├── .env               # Environment variables (not in repo)
├── test_files/        # Sample audio files for testing
└── docs/              # Additional documentation
```

## 🧪 Running Tests

To run the test suite:

```bash
pytest
```

Make sure you have all dependencies installed and your environment variables set up as described above.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a pull request

## 📫 Contact

For questions, suggestions, or support, please open an issue or contact: [davide.magliano98@gmail.com](mailto:davide.magliano98@gmail.com)

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.