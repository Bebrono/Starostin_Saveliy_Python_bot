FROM python:3.9

RUN pip install requests beautifulsoup4 psycopg2-binary

COPY parser.py /app/parser.py

RUN mkdir /var/log/parser
VOLUME ["/var/log/parser"]

CMD ["python", "/app/parser.py"]