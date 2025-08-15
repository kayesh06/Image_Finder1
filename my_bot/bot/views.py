# bot/views.py
import os
import io
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
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
REDIRECT_URI = f'{settings.API_HOST}/oauth2callback/'


# ===== helper =====
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


# ==== GOOGLE LOGIN & AUTH ====
def google_login(request):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent', include_granted_scopes='true')
    return redirect(auth_url)


def oauth2_callback(request):
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials
        request.session['credentials'] = credentials_to_dict(creds)
        return HttpResponse("✅ Google Drive connected. You can now close this tab.")
    except Exception as e:
        return HttpResponse(f"Error during authentication: {str(e)}", status=400)


def auth_status(request):
    return JsonResponse({'authenticated': 'credentials' in request.session})


def build_drive_service_from_session(session):
    creds_data = session.get('credentials')
    if not creds_data:
        return None
    creds = Credentials(**creds_data)
    return build('drive', 'v3', credentials=creds)


# ==== DRIVE HELPERS ====
def get_images_from_drive(service, folder_id=None):
    """
    If folder_id is None or empty, search the entire Drive.
    """
    if folder_id:
        query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    else:
        query = "mimeType contains 'image/'"

    results = service.files().list(
        q=query,
        fields="files(id, name, thumbnailLink)",
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
                'link': f"https://drive.google.com/file/d/{file_id}/view",
                'thumbnail': item.get('thumbnailLink')
            })
        except Exception:
            continue
    return image_list


def find_all_matches(upload_img, drive_images):
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
                'link': it['link'],
                'thumbnail': it.get('thumbnail')
            })
        except Exception:
            continue

    # Sort so highest score first (your request)
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches


# ==== MAIN API ====
@csrf_exempt
def match_image(request):
    if 'credentials' not in request.session:
        return JsonResponse({'error': 'not_authenticated'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    if not request.FILES.get('image'):
        return JsonResponse({'error': 'missing_image'}, status=400)

    folder_id = request.POST.get('folder_id', '').strip()
    service = build_drive_service_from_session(request.session)
    if not service:
        return JsonResponse({'error': 'invalid_credentials'}, status=401)

    try:
        upload_img = Image.open(request.FILES['image']).convert('RGB')
    except Exception:
        return JsonResponse({'error': 'invalid_image'}, status=400)

    drive_images = get_images_from_drive(service, folder_id)
    matches = find_all_matches(upload_img, drive_images)

    # Store in session history
    if 'history' not in request.session:
        request.session['history'] = []
    request.session['history'].append({
        'query_file': request.FILES['image'].name,
        'matches': matches
    })
    request.session.modified = True

    return JsonResponse({
        'status': 'success',
        'matches': matches,
        'total_matches': len(matches)
    })


# ==== HISTORY ENDPOINT ====
@require_GET
def get_history(request):
    return JsonResponse({
        'history': request.session.get('history', [])
    })
