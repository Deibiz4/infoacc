FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (none needed for basic script, but good practice)
# RUN apt-get update && apt-get install -y ...

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY daily_workflow.py .
COPY worker.py .
COPY report_generation_prompt.md .
COPY signal_review_prompt.md .
COPY html_generation_prompt.md .

# Create directories
RUN mkdir -p reports data

# Set volume mount points (though compose handles mapping, this documents intent)
VOLUME /app/reports
VOLUME /app/data

# Run the scheduler
CMD ["python", "-u", "worker.py"]
