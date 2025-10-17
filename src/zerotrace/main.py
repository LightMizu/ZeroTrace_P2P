from zerotrace.kademlia import create_app
from uvicorn import run
import os

# По умолчанию база будет храниться в файле kademlia.db в рабочей папке
db_path = os.environ.get("ZEROTRACE_DB", "kademlia.db")
app = create_app(port=8000, address="0.0.0.0", db_path=db_path)
run(app, host="0.0.0.0", port=8000)