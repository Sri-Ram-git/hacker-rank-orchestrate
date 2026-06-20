import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATASET_DIR = os.path.join(REPO_ROOT, "dataset")
SAMPLE_CLAIMS_PATH = os.path.join(DATASET_DIR, "sample_claims.csv")
CLAIMS_PATH = os.path.join(DATASET_DIR, "claims.csv")
USER_HISTORY_PATH = os.path.join(DATASET_DIR, "user_history.csv")
EVIDENCE_REQUIREMENTS_PATH = os.path.join(DATASET_DIR, "evidence_requirements.csv")
OUTPUT_PATH = os.path.join(REPO_ROOT, "output.csv")

CODE_DIR = os.path.join(REPO_ROOT, "code")
PROMPTS_DIR = os.path.join(CODE_DIR, "prompts")
STRATEGY_A_PROMPT = os.path.join(PROMPTS_DIR, "strategy_a.txt")
STRATEGY_B_PROMPT = os.path.join(PROMPTS_DIR, "strategy_b.txt")

EVALUATION_DIR = os.path.join(REPO_ROOT, "code", "evaluation")
EVALUATION_REPORT_PATH = os.path.join(REPO_ROOT, "evaluation", "evaluation_report.md")

VLM_PROVIDER = os.environ.get("VLM_PROVIDER", "gemini")
VLM_MODEL = os.environ.get("VLM_MODEL", "gemini-2.5-flash")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
