# AI-Powered Design Assistant

This project is an AI-Powered Design Assistant built with Python, leveraging the Streamlit framework. It provides tools and analyses for evaluating design elements related to accessibility, dark patterns, and overall visual appeal.

## Key Features & Benefits

*   **Accessibility Auditing:** Uses `axe-core` to identify accessibility violations.
*   **Dark Pattern Detection:** Analyzes designs for potentially manipulative or unethical patterns.
*   **Visual Appeal Assessment:** (Feature is implied but needs further expansion)
*   **Streamlit Interface:** User-friendly web application for easy interaction.
*   **Configurable Pipeline:** Modular design allows for customization of audit processes.
*   **Audit History Tracking:** Records audit results for future reference and comparison.

## Prerequisites & Dependencies

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.7 or higher is recommended.
*   **pip:** Python package installer.
*   **Streamlit:** For the web application interface.
*   **axe-selenium-python:** (Optional) For accessibility auditing.

You can install the required Python packages using pip:

```bash
pip install streamlit pandas plotly
pip install axe-selenium-python  # Optional: for accessibility audits
```

## Installation & Setup Instructions

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/sainikhils02/des646-project.git
    cd des646-project
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt # Assuming you have a requirements.txt (Create if you don't have it, put all packages to it)
    ```
    If you don't have a requirements file, create a new file called "requirements.txt" in the root of your directory.
    Add these packages into the file:

    ```
    streamlit
    pandas
    plotly
    axe-selenium-python
    ```
    Then run the command:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables (optional):**

    Create a `.env` file in the root directory and define any necessary environment variables, such as API keys or database connection strings.  You can load them using `os.environ` in `app.py`.
    ```
    # .env example
    # API_KEY=your_api_key
    ```

## Usage Examples

1.  **Running the Streamlit application:**

    ```bash
    streamlit run app.py
    ```

    This will start the Streamlit server and open the application in your web browser.

2.  **Using the command-line interface:**

    ```bash
    python -m design_assistant url https://www.example.com
    python -m design_assistant screenshot path/to/screenshot.png
    ```

    Replace `url` and `screenshot` with the appropriate mode and value.

## Configuration Options

*   **Environment Variables:** API keys, database configurations, etc., can be configured using environment variables.
*   **Audit Configuration:**  The `design_assistant/audits` directory contains modules for different audits (accessibility, dark patterns, contrast).  You can modify these modules to customize the audit processes.
*   **Threshold values:** Define threshold values for each of the audits.

## Contributing Guidelines

We welcome contributions to this project! To contribute:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them with clear, concise messages.
4.  Submit a pull request to the main branch.

Please follow these guidelines:

*   Write clear and concise code.
*   Add comments to explain complex logic.
*   Test your changes thoroughly.
*   Follow the existing code style.

## Acknowledgments

*   [Streamlit](https://streamlit.io/) for providing the web application framework.
*   [axe-core](https://www.deque.com/axe/) for accessibility auditing.
*   [Plotly](https://plotly.com/) for data visualization.
*   (Add any other relevant resources or libraries)
