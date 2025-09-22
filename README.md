# ALGORHYTHM

This is the code for my final project Django REST API, a music recommendation system developed off the NextTrack project template.

---

## Data Folder

The `data/` folder contains large files required for running NextTrack (models, embeddings, datasets).  
These files are **not included in the GitHub repository** due to their size.

You can download all required files from Google Drive:  
[Data Files]((https://drive.google.com/drive/folders/1khUtVbyatmDqDkF9PCeWgyWded5AoJbp?usp=share_link))

After downloading, place the files in your local `project/data/` folder so the system works correctly.

---

## Deployment

1. Install Dependencies: Install the dependencies listed in requirements. txt.pip install -r requirements. txt
2. Apply Migrations: python manage.py migrate
3. Run the Development Server: python manage.py runserver 127.0.0. 1. 8080

---

## NOTE:
The `data/` folder structure must remain intact for the system to function correctly. 
This deployment is for local testing; production deployment requires additional configuration.
