# import base64
# import io
# import imagehash
#
# def find_all_matches(upload_img, drive_images):
#     uploaded_hash = imagehash.average_hash(upload_img)
#     matches = []
#
#     for name, img in drive_images:
#         try:
#             img_hash = imagehash.average_hash(img)
#             diff = uploaded_hash - img_hash
#
#             # ➕ Convert image to base64
#             buffer = io.BytesIO()
#             img.save(buffer, format="JPEG")
#             img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
#
#             matches.append({
#                 'name': item['name'],
#                 'score': diff,
#                 'link': item['link'],
#                 'preview': f"https://drive.google.com/uc?id={item['link'].split('/d/')[1].split('/')[0]}"
#             })
#
#         except Exception as e:
#             print(f"Error processing image {name}: {e}")
#             continue
#
#     # Optional: sort by similarity score (lower = more similar)
#     matches.sort(key=lambda x: x['score'])
#
#     return matches
