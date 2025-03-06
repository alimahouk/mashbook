# Mashbook

Mashbook is a web application that provides an interactive chat interface powered by OpenAI's GPT models. It allows users to engage in conversations and highlight any snippet of text within a chat to instantly branch off into a new chat while maintaining context from the previous chat. The highlighted snippet from the parent chat will turn into a hyperlink, linking to the new child chat.

## Features

- Interactive chat interface with real-time updates
- Support for multiple OpenAI GPT models
- User authentication and session management
- Chat history and persistence
- Markdown support for messages
- Responsive design

## Prerequisites

- Python 3.11
- PostgreSQL database
- OpenAI API key (Azure OpenAI supported)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/alimahouk/mashbook.git
    cd mashbook
    ```

2. Create and activate a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use: venv\Scripts\activate
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables:

    ```bash
    cp .env.example .env
    ```

Edit the `.env` file with your configuration values:

- Database credentials
- OpenAI/Azure API settings
- Application settings

## Database Setup

1. Create a PostgreSQL database:

    ```bash
    createdb mashbook
    ```

2. Run the database migrations:

    ```bash
    # Add migration commands here if you have them
    ```

## Running the Application

1. Start the development server:

    ```bash
    flask run
    ```

2. Open your browser and navigate to:

    ```text
    http://localhost:8000
    ```

## Configuration

The application can be configured through environment variables in the `.env` file:

### Database Configuration

- `DB_HOST`: Database host address
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password

### OpenAI/Azure Configuration

- `OPENAI_API_BASE`: OpenAI/Azure API base URL
- `OPENAI_API_KEY`: OpenAI/Azure API key
- `OPENAI_API_TYPE`: API type (e.g., 'azure')
- `OPENAI_API_VERSION`: API version

### Application Configuration

- `FLASK_ENV`: Environment (development/production)
- `FLASK_DEBUG`: Debug mode (1/0)
- `FLASK_RUN_HOST`: Host to run the server on
- `FLASK_RUN_PORT`: Port to run the server on

## Development

### Adding New Features

1. Create new routes in `app/routes.py`
2. Add new modules in `app/modules/`
3. Create templates in `app/templates/`
4. Add static assets in `app/static/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for providing the GPT models
- Flask framework and its extensions
- All contributors and maintainers
