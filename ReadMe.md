# 🔬 AI Research Assistant

A multi-agent research workflow that uses AI to break down complex questions, search the web, synthesize information, and suggest follow-up questions. Built with LangGraph, OpenAI GPT-4, and Gradio.

## ✨ Features

- **Multi-Agent Architecture**: Uses LangGraph to orchestrate a workflow of specialized agents
- **Intelligent Query Analysis**: Breaks down complex questions into targeted search queries
- **Web Search Integration**: Uses Serper API for real-time web search results
- **Content Synthesis**: AI-powered summarization of multiple sources with citations
- **Follow-up Suggestions**: Generates thoughtful questions to deepen research
- **Interactive Web UI**: Clean Gradio interface for easy interaction
- **Error Handling**: Robust error management throughout the workflow

## 🏗️ Architecture

The system uses a graph-based workflow with four main agents:

1. **Query Analyzer** - Breaks down user questions into 3 precise search queries
2. **Search Executor** - Performs web searches using Serper API
3. **Content Synthesizer** - Combines and summarizes search results
4. **Follow-up Generator** - Creates 2 relevant follow-up questions

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ **OR** Docker and Docker Compose
- OpenAI API key
- Serper API key (for web search)

### Option 1: Docker (Recommended)

1. Clone the repository:
```bash
git clone <your-repo-url>
cd multi-agent-search
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run with Docker Compose:
```bash
docker-compose up -d
```

4. Access the application at `http://localhost:7860`

To stop the application:
```bash
docker-compose down
```

### Option 2: Local Python Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd multi-agent-search
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```env
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### Usage

#### Web Interface (Recommended)

Launch the Gradio web app:
```bash
python main.py
```

Then open your browser to `http://localhost:7860`

#### Command Line Interface

Run research queries directly from the command line:
```bash
python agents.py "What are the latest developments in quantum computing?"
```

## 📁 Project Structure

```
multi-agent-search/
├── main.py              # Gradio web interface
├── agents.py            # Core agent workflow (CLI version)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker container configuration
├── docker-compose.yml   # Docker Compose orchestration
├── .env                 # Environment variables (not tracked)
├── .env.example         # Example environment file
├── .dockerignore        # Docker build ignore rules
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🛠️ Key Components

### [`SerperSearchTool`](main.py)
- Handles web search API calls to Serper
- Configurable number of results (default: 5 for web UI, 10 for CLI)
- Returns structured search results with title, URL, and content

### [`ResearchState`](main.py)
- TypedDict that maintains workflow state
- Tracks user query, search results, summaries, and errors
- Enables state passing between agents

### Pydantic Models
- [`SearchQueries`](main.py) - Structured search query generation
- [`ResearchSummary`](main.py) - Formatted research synthesis
- [`FollowUpQuestions`](main.py) - Generated follow-up questions

## 🎯 Example Queries

- "What are the latest developments in quantum computing?"
- "How does climate change affect ocean ecosystems?"
- "What are the best practices for remote team management?"
- "Explain the difference between machine learning and deep learning"

## 🔧 Configuration

### Search Results
Modify the number of search results in [`main.py`](main.py):
```python
search_tool = SerperSearchTool(k=5)  # Adjust as needed
```

### AI Model
Change the OpenAI model in both files:
```python
LLM = ChatOpenAI(model="gpt-4o", temperature=0)  # Use different model
```

### Web Interface Port
Modify the Gradio launch settings in [`main.py`](main.py):
```python
app.launch(
    share=False,
    server_name="0.0.0.0",
    server_port=7860  # Change port here
)
```

## 🐳 Docker Deployment

### Building and Running with Docker

1. **Build the Docker image:**
```bash
docker build -t ai-research-assistant .
```

2. **Run the container:**
```bash
docker run -d \
  --name ai-research-assistant \
  -p 7860:7860 \
  --env-file .env \
  ai-research-assistant
```

3. **View logs:**
```bash
docker logs -f ai-research-assistant
```

4. **Stop and remove:**
```bash
docker stop ai-research-assistant
docker rm ai-research-assistant
```

### Using Docker Compose (Recommended)

Docker Compose provides easier management and includes additional features:

1. **Start the application:**
```bash
docker-compose up -d
```

2. **View logs:**
```bash
docker-compose logs -f
```

3. **Stop the application:**
```bash
docker-compose down
```

4. **Rebuild and restart:**
```bash
docker-compose up -d --build
```

### Docker Environment Variables

The Docker setup uses the same environment variables as the local installation. Make sure your `.env` file contains:

```env
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

### Docker Production Tips

- The container runs as a non-root user for security
- Health checks are included to monitor application status
- The application data is stored in a Docker volume for persistence
- Use `docker-compose.override.yml` for local development customizations

## 🐳 Docker Deployment

### Quick Start with Docker

1. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. **Start the application:**
```bash
docker-compose up -d
```

3. **Access the app:** Open `http://localhost:7860` in your browser

### Docker Commands

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start in background |
| `docker-compose up` | Start with logs visible |
| `docker-compose down` | Stop the application |
| `docker-compose logs -f` | View live logs |
| `docker-compose ps` | Check container status |
| `docker-compose build` | Rebuild the image |
| `docker-compose restart` | Restart the service |

### Development with Docker

For development with live code changes:
1. Uncomment the volume mount in `docker-compose.yml`
2. Restart: `docker-compose down && docker-compose up -d`

## 🔐 API Keys Setup

### OpenAI API Key
1. Sign up at [OpenAI](https://platform.openai.com/)
2. Generate an API key
3. Add to `.env` file

### Serper API Key
1. Sign up at [Serper](https://serper.dev/)
2. Get your API key
3. Add to `.env` file

## 🐛 Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure both OpenAI and Serper API keys are set in `.env`
2. **Port Already in Use**: Change the port in `app.launch()` if 7860 is occupied
3. **Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
4. **Rate Limits**: Both APIs have rate limits - consider implementing delays if needed

### Error Handling

The system includes comprehensive error handling:
- API failures are caught and logged
- Workflow continues even if individual steps fail
- Errors are displayed in both CLI and web interface

## 📊 Dependencies

Key dependencies include:
- `langchain-openai`: OpenAI integration
- `langgraph`: Multi-agent workflow orchestration
- `gradio`: Web interface
- `pydantic`: Data validation
- `requests`: HTTP requests for search API
- `python-dotenv`: Environment variable management

See [`requirements.txt`](requirements.txt) for complete list.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source. Please check the license file for details.

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for multi-agent orchestration
- Uses [Serper API](https://serper.dev/) for web search capabilities
- Web interface powered by [Gradio](https://gradio.app/)
- AI capabilities from [OpenAI GPT-4](https://openai.com/)