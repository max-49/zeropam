import sqlite3
from wordcloud import WordCloud

# --- CONFIGURATION ---
DB_PATH = "logins.db"
TABLE_NAME = "passwords"
COLUMN_NAME = "password"
OUTPUT_FILE = "password_wordcloud.png"

# --- CONNECT TO DATABASE ---
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"[+] Connected to database: {DB_PATH}")
except sqlite3.Error as e:
    print(f"[!] Database connection failed: {e}")
    exit(1)

# --- FETCH PASSWORDS ---
try:
    cursor.execute(f"SELECT {COLUMN_NAME} FROM {TABLE_NAME}")
    rows = cursor.fetchall()
    if not rows:
        print("[!] No passwords found in the table.")
        exit(0)
except sqlite3.Error as e:
    print(f"[!] Database query failed: {e}")
    exit(1)
finally:
    conn.close()

# --- PREPARE TEXT DATA ---
passwords = [row[0] for row in rows if isinstance(row[0], str)]
text = " ".join(passwords)

if not text.strip():
    print("[!] No valid text data found in the password column.")
    exit(0)

# --- GENERATE WORD CLOUD ---
# --- CUSTOM COLOR FUNCTION FOR BETTER CONTRAST ---
def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    import random
    random.seed(hash(word))
    # Dark colors that show well on white background
    colors = [
        'rgb(139,0,0)',      # dark red
        'rgb(0,0,139)',      # dark blue
        'rgb(139,0,139)',    # dark magenta
        'rgb(0,100,0)',      # dark green
        'rgb(139,69,19)',    # saddle brown
        'rgb(75,0,130)',     # indigo
        'rgb(128,0,0)',      # maroon
        'rgb(0,128,128)',    # teal
    ]
    return random.choice(colors)

# --- GENERATE WORD CLOUD ---
wordcloud = WordCloud(
    width=1400,               # moderate size
    height=1000,
    background_color="white",
    collocations=False,
    regexp=r"[^ ]+",          # keep special characters
    include_numbers=True,
    normalize_plurals=False,
    max_words=2000,
    scale=2,# reduced from 500
    min_word_length=1,
    repeat=False,
    margin=1,
    stopwords=["Whoami"]
).generate(text)

# Apply custom colors
wordcloud.recolor(color_func=color_func)

# --- SAVE TO IMAGE FILE ---
wordcloud.to_file(OUTPUT_FILE)
print(f"[+] Word cloud saved as: {OUTPUT_FILE}")
