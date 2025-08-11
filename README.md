# youtrack-catchup

A tool to quickly catch up on things that happened in YouTrack.
It is meant to provide a list of issues that require the user's attention.

## Motivation

YouTrack email notifications, at least in the default configuration, generate a lot of noise and are barely useful.
The notifications tab within YouTrack is better, but it's based on the read/unread status of messages.

What I want instead is a list of actionable items related to issues that tell me what I'm expected to do about them.

## Quick Start

### Prerequisites

- Python 3.13 or higher
- Poetry (for dependency management)
- A YouTrack account with API access
- An OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dsdolzhenko/youtrack-catchup.git
   cd youtrack-catchup
   ```

2. **Install dependencies using Poetry**
   ```bash
   poetry install
   ```

3. **Set up your environment variables**
   ```bash
   cp .env.template .env
   ```

   Edit the `.env` file with your credentials:
   - `YOUTRACK_URL`: Your YouTrack instance URL (e.g., `https://yourcompany.youtrack.cloud`)
   - `YOUTRACK_TOKEN`: Your YouTrack permanent token ([How to get a token](https://www.jetbrains.com/help/youtrack/server/manage-permanent-token.html))
   - `OPEN_AI_TOKEN`: Your OpenAI API key ([Get your API key](https://platform.openai.com/api-keys))

### Usage

Run the tool to get your personalized YouTrack catch-up summary:

```bash
poetry run python -m youtrack_catchup --actions
```

The tool will:
1. Connect to your YouTrack instance
2. Fetch recent issues requiring your attention
3. Use AI to analyze and summarize actionable items
4. Display a prioritized list of what needs your attention

To see all the available options:

```bash
poetry run python -m youtrack_catchup --help
```

## License

The project is licensed under [the MIT license](LICENSE.txt).
