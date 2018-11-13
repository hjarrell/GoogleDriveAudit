import sys

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient import errors


SCOPES = 'https://www.googleapis.com/auth/drive'
STARTING_FOLDER_NAME = 'Classes'
MAX_OWNERS = 0

OUTPUT_STR = ''

def main():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('drive', 'v3', http=creds.authorize(Http()))

    results = service.files().list(q="name='{}' and mimeType = 'application/vnd.google-apps.folder'".format(STARTING_FOLDER_NAME),
        fields='nextPageToken, files(id, name)').execute()
    items = results.get('files', [])


    starting_folder_id = None
    if not items:
        print('ERROR: Starting folder not found')
        sys.exit(1)
    else:
        starting_folder_id = items[0]['id']
    
    if starting_folder_id is not None:
        crawl_drive(service, starting_folder_id, STARTING_FOLDER_NAME + '/')
        print('"File Name"\t"File Path"\t"Owners"' + '\t'*MAX_OWNERS +'"Permissions"')
        print(OUTPUT_STR)
    else:
        print('ERROR: Starting folder id not found')
        sys.exit(1)

def get(l, some, none):
    try:
        return l[some]
    except KeyError as e:
        return none

def crawl_drive(service, starting_folder_id, current_path):
    global MAX_OWNERS
    global OUTPUT_STR
    page_token = None
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            children = service.files().list(q="'{}' in parents".format(starting_folder_id),
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, owners, permissions)',
                pageToken=page_token
            ).execute()

            folders = []
            for file in children.get('files', []):
                is_folder = file['mimeType'] == 'application/vnd.google-apps.folder'
                file_id = file['id']
                name = file['name'].replace('"', '')
                full_path = current_path + name
                owners = get(file, 'owners', [])
                owner_output = ''
                for owner in owners:
                    owner_output += owner['displayName'] + '|' + owner['emailAddress'] + '\t'
                if len(owners) > MAX_OWNERS:
                    MAX_OWNERS = len(owners)

                permissions = get(file, 'permissions', [])
                permission_output = ''
                for permission in permissions:
                    permission_output += get(permission, 'displayName', '') + '|' + get(permission, 'emailAddress','') + '|' + permission['role'] + '\t'

                OUTPUT_STR += ('{}\t{}\t{}\t{}\n'.format(name, full_path, owner_output, permission_output))
                if is_folder:
                    folders.append((name, file_id))
            
            if len(folders) > 0:
                for folder in folders:
                    crawl_drive(service, folder[1], current_path + folder[0] + '/')

            page_token = children.get('nextPageToken')
            if not page_token:
                break
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
            break
        except KeyError as e:
            pass

if __name__ == '__main__':
    main()
