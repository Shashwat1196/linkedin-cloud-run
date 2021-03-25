import time
import json
from flask import Flask, request


app = Flask(__name__)

# @app.route("/", methods=["GET"])
# def hello():
#     """ Return a friendly HTTP greeting. """
#     who = request.args.get("who", "World")
#     return f"Hello {who}!\n"


LINKEDIN_APP_KEY = '78tr4a8w4zzg6i'
LINKEDIN_APP_SECRET = 'NWN0OkcX5PjEPAcU'

class Linkedin:
    MAX_RETRIES = 2
    RETRY_INTERVAL = 5
    EXCEPTION_CODE = 0
    NO_RESPONSE = 'No response from linkedin'


    def __init__(self, member):
        self.member = member 
        self.access_token, self.refresh_token = self.get_social_account()
        self.headers = {'Authorization': 'Bearer ' + self.access_token}
        self.is_access_token_refreshed = False
        self.url = 'https://api.linkedin.com/v2/'


    def decrypt_token(self, token):
        hash_salt = settings.HASH_SALT
        secret_key = generate_secret_key(hash_salt)
        cipher = AESCipher(secret_key)
        decrypt_token = cipher.decrypt(token)
        return decrypt_token


    def encrypt_token(self, token):
        hash_salt = settings.HASH_SALT
        secret_key = generate_secret_key(hash_salt)
        cipher = AESCipher(secret_key)
        encrypt_token = cipher.encrypt(token)
        return encrypt_token


    def _get(self, uri):
        max_retries = Linkedin.MAX_RETRIES
        while max_retries:
            max_retries -= 1
            try:
                endpoint = self.url + uri
                response = requests.get(endpoint, headers=self.headers)
                if response.status_code == 401 and not self.is_access_token_refreshed:
                    access_token = self.get_refresh_access_token()
                    if access_token is None:
                        return
                    self.is_access_token_refreshed = True
                    access_token = self.decrypt_token(access_token)
                    self.headers = {'Authorization': 'Bearer ' + access_token}
                    response = self._get(uri)
                return response
            except ConnectionError:
                if max_retries == 0:
                    raise
                time.sleep(Linkedin.RETRY_INTERVAL)
            except Exception:
                if max_retries == 0:
                    raise
                time.sleep(Linkedin.RETRY_INTERVAL)


    def get_refresh_access_token(self):
        max_retries = Linkedin.MAX_RETRIES
        endpoint = 'https://www.linkedin.com/oauth/v2/accessToken'
        while max_retries:
            max_retries -= 1
            try:
                response = requests.post(endpoint, 
                                        headers={'content-type':'application/x-www-form-urlencoded'}, 
                                        data = {
                                                "grant_type": "refresh_token",
                                                "refresh_token": self.refresh_token,
                                                "client_id": LINKEDIN_APP_KEY,
                                                "client_secret": LINKEDIN_APP_SECRET
                                        }
                                    )
            except ConnectionError:
                if max_retries == 0:
                    return
                time.sleep(Linkedin.RETRY_INTERVAL)
            except Exception:
                if max_retries == 0:
                    return
                time.sleep(Linkedin.RETRY_INTERVAL)

        if response.status_code != 200:
            return
        json_text = response.text
        data = json.loads(json_text)
        access_token = data['access_token']
        access_token = self.encrypt_token(access_token)
        return access_token


    def get_error_msg(self, response):
        try:
            if isinstance(response.json() ,list):
                error_msg = response.json()[0].get('message')
            else: 
                error_msg = response.json().get('message')
        except:
            error_msg = 'Something went wrong'
        return None, error_msg


    def get_formatted_ids(post_ids, summary=False):
        if summary:
            formatted_ids = '&'.join(['ids=' + post_id for post_id in post_ids])
        else:
            formatted_ids = '&'.join(['ids=' + post_id.split(":")[-1] for post_id in post_ids])
        return formatted_ids


    def get_linkedin_articles(self, post_ids):
        if not post_ids:
            return "No Post Ids present"

        formatted_ids = self.get_formatted_ids(post_ids)
        endpoint = 'shares?{post_ids}'.format(post_ids=formatted_ids)
        try:
            response = self._get(endpoint)
            if response is None:
                return None, Linkedin.NO_RESPONSE
        except Exception as e:
            return None, str(e)
        if response.status_code != 200:
            return self.get_error_msg(response)
        json_text = response.text
        data = json.loads(json_text)
        return data, None


    def get_article_summary(self, post_ids):
        if post_ids:
            formatted_ids = self.get_formatted_ids(post_ids, summary=True)
        endpoint = 'socialActions?{post_id}'.format(post_id=formatted_ids)
        try:
            response = self._get(endpoint)
            if response is None:
                return None, Linkedin.NO_RESPONSE
        except Exception as e:
            return None, str(e)
        if response.status_code != 200:
            return self.get_error_msg(response)

        json_text = response.text
        data = json.loads(json_text)
        return data, None


    def get_batch_linkedin_articles(self, post_ids):
        if not post_ids:
            return "No Post IDs are present"
        chunk_size = 50
        list_of_post_data = []
        for i in range(0, len(post_ids), chunk_size):
            post_data = self.get_linkedin_articles(post_ids[i:i + chunk_size])
            post_summary_data = self.get_article_summary(post_ids[i:i + chunk_size])

            post_data_result = post_data["results"]
            post_summary_result = post_summary_data["results"]

            for i in range(len(post_summary_result.keys())):
                id = post_summary_result.keys()[i]
                summary = post_summary_result[id]
                like_count = summary['likesSummary']['totalLikes']
                comment_count = summary['commentsSummary']['aggregatedTotalComments']
                firstlevelcomment_count = summary['commentsSummary']['totalFirstLevelComments']
                reply_count = comment_count - firstlevelcomment_count
                
                post_id = id.split(":")[-1]
                post = post_data_result[post_id]
                content = post['text']['text']
                link_url = post["content"]["contentEntities"][0]["entityLocation"]
                link_text = post["content"]["title"]
                created = post["created"]["time"]
                last_modified = post["lastModified"]["time"]
            
                list_of_post_data.append({
                    "id": id,
                    "like_count":like_count,
                    "comment_count": comment_count,
                    "firstlevelcomment_count": firstlevelcomment_count,
                    "reply_count":reply_count,
                    "content":content,
                    "link_url":link_url,
                    "link_text": link_text,
                    "linkedin_modified_utc": last_modified,
                    "linkedin_created_utc": created
                })
        return list_of_post_data



if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)
