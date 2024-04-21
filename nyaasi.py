import feedparser
import requests, time, os
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, send_file
import concurrent.futures

app = Flask(__name__)


def parse_nyaasi_feed(query, page=1):
    # # Convert the query to URL-friendly format
    # query = urllib.parse.quote_plus(query)
    # print(query)
    # # Construct the feed URL with the query and page options
    feed_url = f'https://nyaa.si/?page=rss&q={query}'

    feed = feedparser.parse(feed_url)
    entries = feed.entries
    results = []
    for entry in entries:
        title = entry.title
        magnet_link = entry.links[0].href
        nyaasi_link = entry.link
        torrent_id = entry.id.split('/')[-1]
        seeders = entry.nyaa_seeders
        leechers = entry.nyaa_leechers
        downloads = entry.nyaa_downloads
        infohash = entry.nyaa_infohash
        category_id = entry.nyaa_categoryid
        category = entry.nyaa_category
        size = entry.nyaa_size
 
        results.append({
            'title': title,
            'magnet_link': magnet_link,
            'nyaasi_link': nyaasi_link,
            'torrent_id': torrent_id,
            'seeders': seeders,
            'leechers': leechers,
            'downloads': downloads,
            'infohash': infohash,
            'category_id': category_id,
            'category': category,
            'size': size
        })
    return results

def process_entry(entry):
    nyaa_link = entry.id
    response = requests.get(nyaa_link)
    soup = BeautifulSoup(response.content, "html.parser")
    magnet_link_element = soup.select_one('a[href^="magnet:?xt="]')
    if magnet_link_element is not None:
        magnet_link = magnet_link_element['href']
    else:
        magnet_link = None
    title_element = soup.select_one('div.panel-heading h3')
    if title_element is not None:
        title = title_element.text.strip()
    else:
        title = None
    return {
        "Magnet Link": magnet_link,
        "Title": title
    }


#download?link=
@app.route('/download', methods=['GET'])
def download_file():
    download_link = request.args.get('link')
    if not download_link:
        return {'code':404}
    response = requests.get(download_link)
    if response.status_code != 200:
        return{'code':404}
    filename = f'downloaded_file_{int(time.time())}.torrent'
    with open(filename, 'wb') as f:
        f.write(response.content)
    hosted_url = f'http://nyaasi.akeno.fun/{filename}' 
    return {'code':hosted_url}

#upload?file=file_name
@app.route('/upload', methods=['GET'])
def upload_file():
    filename = request.args.get('file')
    if not filename:
        return {'code':404}
    if not os.path.exists(filename):
        return {'code':404 }
    return send_file(filename, as_attachment=True)

@app.route('/remove', methods=['GET'])
def remove_file():
    filename = request.args.get('file')
    if not filename:
        return  {'code':404}
    if not os.path.exists(filename):
        return  {'code':404}
    os.remove(filename)
    
    return  {'code':200}

#feed?q=rest_url
@app.route('/feed', methods=['GET'])
def get_feeds():
    get_text = request.full_path.split('?q=')[1]  
    return parse_nyaasi_feed(get_text) 

@app.route('/magnet', methods=['GET'])
def get_magnet():
    get_text = request.full_path.split('?q=')[1]
    # get_text = get_text.replace(' ', '+')  # Convert spaces to URL format
    # get_text = get_text.replace('%20', '+')  # Convert spaces to URL format

    rss_feed_url = f"http://nyaa.si/?page=rss&q={get_text}"
    print(rss_feed_url)
    feed = feedparser.parse(rss_feed_url)
    
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_entry, entry) for entry in feed.entries]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result["Title"] and result["Magnet Link"]:
                    results.append(result)
            except Exception as e:
                print("Error processing entry:", e)

    return jsonify(results)

if __name__ == '__main__':
    app.run()
