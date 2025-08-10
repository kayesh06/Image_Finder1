# bot/views.py
import os
import io
import json
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image
import imagehash
from django.conf import settings


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# ==== CONFIG ====
CLIENT_SECRET_FILE = os.path.join(settings.BASE_DIR, 'client_secret.json')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
REDIRECT_URI = f'{settings.API_HOST}/oauth2callback/'  # Use a dynamic host


# ===== helper =====
def credentials_to_dict(credentials):
    """
    Serializes Credentials object to a dictionary for session storage.
    """
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


# ==== GOOGLE LOGIN & AUTHENTICATION ====
def google_login(request):
    """
    Redirects user to Google OAuth consent page.
    """
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent', include_granted_scopes='true')
    return redirect(auth_url)


def oauth2_callback(request):
    """
    Google redirects here after user consents. We fetch the token and store credentials in the Django session.
    """
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        request.session['credentials'] = credentials_to_dict(creds)

        return HttpResponse("✅ Google Drive connected. You can now close this tab and go back to the extension.")
    except Exception as e:
        return HttpResponse(f"Error during authentication: {str(e)}", status=400)


def auth_status(request):
    """
    An endpoint to check the Google login status.
    """
    authenticated = 'credentials' in request.session
    return JsonResponse({'authenticated': authenticated})


# ==== DRIVE helpers ====
def build_drive_service_from_session(session):
    creds_data = session.get('credentials')
    if not creds_data:
        return None
    creds = Credentials(**creds_data)
    service = build('drive', 'v3', credentials=creds)
    return service


def get_images_from_drive(service, folder_id):
    """
    Lists images in a folder and downloads them to memory.
    """
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'image/'",
            fields="files(id, name)",
            pageSize=1000
        ).execute()
        items = results.get('files', [])
        image_list = []
        for item in items:
            file_id = item['id']
            file_name = item['name']
            request_media = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request_media)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            try:
                img = Image.open(fh).convert('RGB')
                image_list.append({
                    'id': file_id,
                    'name': file_name,
                    'image': img,
                    'link': f"https://drive.google.com/file/d/{file_id}/view"
                })
            except Exception:
                # skip unreadable files
                continue
        return image_list
    except Exception as e:
        raise Exception(f"Failed to retrieve images from Drive: {e}")


def find_all_matches(upload_img, drive_images):
    """
    Compares the uploaded image hash to all images in the folder.
    """
    uploaded_hash = imagehash.average_hash(upload_img)
    matches = []
    for it in drive_images:
        try:
            img_hash = imagehash.average_hash(it['image'])
            diff = uploaded_hash - img_hash
            matches.append({
                'id': it['id'],
                'name': it['name'],
                'score': int(diff),
                'link': it['link']
            })
        except Exception:
            continue
    matches.sort(key=lambda x: x['score'])
    return matches


# ==== API ENDPOINTS ====
@csrf_exempt
def match_image(request):
    """
    POST: Expects 'image' file and 'folder_id'.
    """
    if 'credentials' not in request.session:
        return JsonResponse({'error': 'not_authenticated', 'message': 'Please login first'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    if not request.FILES.get('image') or not request.POST.get('folder_id'):
        return JsonResponse({'error': 'missing_params', 'message': 'Provide image file and folder_id'}, status=400)

    service = build_drive_service_from_session(request.session)
    if service is None:
        return JsonResponse({'error': 'invalid_credentials'}, status=401)

    uploaded_file = request.FILES['image']
    try:
        upload_img = Image.open(uploaded_file).convert('RGB')
    except Exception:
        return JsonResponse({'error': 'invalid_image'}, status=400)

    folder_id = request.POST['folder_id'].strip()
    try:
        drive_images = get_images_from_drive(service, folder_id)
    except Exception as e:
        return JsonResponse({'error': 'drive_error', 'message': str(e)}, status=500)

    matches = find_all_matches(upload_img, drive_images)
    return JsonResponse({'status': 'success', 'matches': matches, 'total_matches': len(matches)})