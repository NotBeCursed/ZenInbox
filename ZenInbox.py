#! /usr/bin/env python3

import base64
import email
import os.path
import sys
from ollama import Client, ChatResponse
from gpt import ChatGPT

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List
from typing_extensions import TypedDict


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_FILE = f'{os.path.dirname(os.path.realpath(__file__))}/token.json'
CREDENTIALS_FILE = f'{os.path.dirname(os.path.realpath(__file__))}/credentials.json'

class Mail(TypedDict):
    mailId:str
    mailThreadID:str
    mailSender:str
    mailObject:str
    mailContent:str

class ZenInbox():
    def __init__(self, user:str = 'me', labels:list[str] = ['commercial', 'service', 'personnel', 'newsletter', 'autre', 'professionnel'], offline:bool = False, offline_ai_model:str = 'mistral', offline_ai_host:str = 'http://localhost:11434', scope:str = SCOPES) -> None:

        # Setup GMAIL API
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, scope)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        self.user = user
        self.offline = offline
        self.offline_ai_model = offline_ai_model
        self.OllamaClient = Client(offline_ai_host)
        self.labels = labels
        self.labelsId = {}

    def get_inboxMails(self) -> List[Mail] :
        """ Returns the list of inbox mails where each value is a dictionary containing the mailId, mailThreadId, mailSender, mailObject, and mailContent."""

        inboxMails = []

        message = self.service.users().messages().list(userId=self.user, labelIds=['INBOX']).execute()
        if message['resultSizeEstimate'] == 0:
            return None
        
        for mail in message['messages']:
            mailId = mail['id']
            mailThreadId = mail['threadId']
            
            # GET MAIL SENDER AND OBJECT 
            mailData = self.service.users().messages().get(userId=self.user, id=mailId, format='metadata').execute()
            mailHeaders = mailData.get('payload', {}).get('headers', [])
            for header in mailHeaders:
                if header.get('name') == 'Subject':
                    mailObject = header.get('value')
                else:
                    mailObject = 'Mail object not found'
                if header.get('name') == "From":
                    mailSender = header.get('value')
                else:
                    mailSender = 'Mail sender not found'

            # GET MAIL CONTENT
            mailRaw = self.service.users().messages().get(userId=self.user, id=mailId, format='raw').execute()
            mailStr = base64.urlsafe_b64decode(mailRaw['raw'].encode('utf-8')).decode('utf-8', errors='replace')
            mailMime = email.message_from_string(mailStr)
            mailContent = ""

            if mailMime.is_multipart():
                for part in mailMime.walk():
                    contentType = part.get_content_type()
                    contentDisposition = str(part.get('Content-Disposition'))
                    if contentType == 'text/plain' and 'attachment' not in contentDisposition:
                        mailContent = part.get_payload(decode=True)
                        if mailContent:
                            mailContent = mailContent.decode('utf-8', errors='replace')
                            break
            else:
                mailContent = mailMime.get_payload(decode=True)
                if mailContent:
                            mailContent = mailContent.decode('utf-8', errors='replace')

            inboxMails.append({
                'mailId': mailId, 
                'mailThreadId': mailThreadId,
                'mailSender' : mailSender,
                'mailObject': mailObject,
                'mailContent' : mailContent
            })
  
        
        while 'nextPageToken' in message:
            message = self.service.users().messages().list(userId="me", labelIds=['INBOX'], pageToken=message["nextPageToken"]).execute()
            for mail in message['messages']:
                mailId = mail['id']
                mailThreadId = mail['threadId']
                
                # GET MAIL SENDER AND OBJECT 
                mailData = self.service.users().messages().get(userId=self.user, id=mailId, format='metadata').execute()
                mailHeaders = mailData.get('payload', {}).get('headers', [])
                for header in mailHeaders:
                    if header.get('name') == 'Subject':
                        mailObject = header.get('value')
                    else:
                        mailObject = 'Mail object not found'
                    if header.get('name') == "From":
                        mailSender = header.get('value')
                    else:
                        mailSender = 'Mail sender not found'

                # GET MAIL CONTENT
                mailRaw = self.service.users().messages().get(userId=self.user, id=mailId, format='raw').execute()
                mailStr = base64.urlsafe_b64decode(mailRaw['raw'].encode('utf-8')).decode('utf-8', errors='replace')
                mailMime = email.message_from_string(mailStr)
                mailContent = ""

                if mailMime.is_multipart():
                    for part in mailMime.walk():
                        contentType = part.get_content_type()
                        contentDisposition = str(part.get('Content-Disposition'))
                        if contentType == 'text/plain' and 'attachment' not in contentDisposition:
                            mailContent = part.get_payload(decode=True)
                            if mailContent:
                                mailContent = mailContent.decode('utf-8', errors='replace')
                                break
                else:
                    mailContent = mailMime.get_payload(decode=True)
                    if mailContent:
                                mailContent = mailContent.decode('utf-8', errors='replace')

                inboxMails.append({
                    'mailId': mailId, 
                    'mailThreadId': mailThreadId,
                    'mailSender' : mailSender,
                    'mailObject': mailObject,
                    'mailContent' : mailContent
                })

        return inboxMails

    def get_label_offline(self, mailSender:str, mailObject:str, mailContent:str) -> str :
        """Use Ollama local AI to evaluate a mail and return an appropriate label."""

        if not mailSender: 
            mailSender = "expéditeur non trouvé"
            if not mailObject: 
                mailObject = "objet non trouvé"

            try:
                response: ChatResponse = self.OllamaClient.chat(
                    model="mistral",
                    messages=[
                        {
                            "role": "user",
                            "content": f"""
                                Catégorise cet email de manière autonome, et retourne uniquement le mot correspondant à la catégorie que tu as déterminée, sans aucune explication ou texte additionnel.
                                
                                Voici l'expéditeur : {mailSender}
                                Voici l'objet : {mailObject}
                                Voici le contenu du mail : {mailContent}

                                Retourne simplement la catégorie exacte que tu as trouvée, entre guillemets, sans mise en forme de ta part, parmis la liste suivante : {self.labels}.
                            """
                        }
                    ]
                )
                return response['message']['content'].strip()
            except Exception as e:
                print(f"Erreur lors de l'appel à Ollama : {e}")
                return "Erreur"

    def get_label(self, mailSender:str, mailObject:str, mailContent:str) -> str:
        """Use ChatGPT to evaluate a mail and return an appropriate label."""

        if mailContent and len(mailContent) > 1000:
            mailContent = mailContent[:1000] + '... [contenu tronqué]'

        label = ChatGPT.request(f"""
                                Catégorise cet email de manière autonome, et retourne uniquement le mot correspondant à la catégorie que tu as déterminée, sans aucune explication ou texte additionnel.
                                
                                Voici l'expéditeur : {mailSender}
                                Voici l'objet : {mailObject}
                                Voici le contenu : {mailContent}

                                Retourne simplement la catégorie exacte que tu as trouvée, sans mise en forme de ta part,parmis la liste suivante : {self.labels}.
                            """)
        return label

    def create_gmailLabels(self, mlv='show', llv='labelShow') -> None:
        """Create labels in Gmail."""

        for labelName in self.labels:
            label = {
                "messageListVisibility" : mlv,
                "labelListVisibility" : llv,
                "name" : labelName
            }
            labelId = None
            try : 
                self.service.users().labels().create(userId=self.user, body=label).execute() # CREATE LABEL IF NOT ALREADY CREATED
            except Exception as error:
                print(f'Error : {error}')

            # GET LABEL ID
            response = self.service.users().labels().list(userId=self.user).execute()
            for label in response['labels']:
                if label['name'] == labelName:
                    labelId = label['id']
            self.labelsId[labelName] = labelId
            
    def apply_label(self, labelName:str, mailId:str) -> None:
        """Apply a Gmail label on a mail."""

        try:
            labelId = self.labelsId[labelName]
            self.service.users().messages().modify(userId=self.user, id=mailId, body={'removeLabelIds': ["INBOX"], 'addLabelIds': [labelId]}).execute()
            print(f'Mail {mailId} add in {labelName} ({labelId})')
        except Exception as error:
            print(f'Label apply error : {error}')
    
    def run(self, as_cron:bool = False) -> None:
        """Launch ZenInbox Bot."""

        self.create_gmailLabels()
        print(self.labelsId)
        
        if as_cron:
            inboxMails = self.get_inboxMails()
            label = None
            if inboxMails:
                for mail in inboxMails:
                    if self.offline: 
                        label = self.get_label_offline(mailSender=mail['mailSender'], mailObject=mail['mailObject'], mailContent=mail['mailContent'])
                    else :
                        label = self.get_label(mailSender=mail['mailSender'], mailObject=mail['mailObject'], mailContent=mail['mailContent'])
                
                    if label.lower() in self.labels:
                        self.apply_label(labelName=label.lower(), mailId=mail['mailId'])
        
        else:
            while True:
                inboxMails = self.get_inboxMails()
                label = None
                if inboxMails:
                    for mail in inboxMails:
                        if self.offline: 
                            label = self.get_label_offline(mailSender=mail['mailSender'], mailObject=mail['mailObject'], mailContent=mail['mailContent'])
                        else :
                            label = self.get_label(mailSender=mail['mailSender'], mailObject=mail['mailObject'], mailContent=mail['mailContent'])
                    
                        if label.lower() in self.labels:
                            self.apply_label(labelName=label.lower(), mailId=mail['mailId'])
            

if __name__ == '__main__':
    
    args = sys.argv
    print(args)
    if '--cron' in args:
        ZenInbox(labels=['professionnel', 'personnel', 'newsletter', 'facture', 'service', 'assurance', 'banque', 'autre']).run(as_cron=True)
    else:
        ZenInbox(labels=['professionnel', 'personnel', 'newsletter', 'facture', 'service', 'assurance', 'banque', 'autre']).run()