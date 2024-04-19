import feedparser
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
import concurrent.futures

app = Flask(__name__)

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

@app.route('/feeds', methods=['GET'])
def get_feeds():
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
    app.run(port=4000)
