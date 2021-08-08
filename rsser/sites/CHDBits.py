import re
import time

import feedparser
import requests
from bs4 import BeautifulSoup

from utils import *


def CHDBits(config):
    response = requests.get(
        config["CHDBits"]["rss"],
        proxies=config["CHDBits"]["proxies"],
        timeout=config["CHDBits"]["rss_timeout"],
    )
    if response.status_code == 200:
        feed = feedparser.parse(response.text)
    else:
        raise Exception
    torrents = {
        re.search("id=(\d+)", entry["link"]).group(1): {
            "site": "CHDBits",
            "title": entry["title"],
            "size": size_G(re.search("\[([\w\.\s]+)\]$", entry["title"]).group(1)),
            "publish_at": time.mktime(entry["published_parsed"]) - time.timezone,
            "link": entry["links"][1]["href"],
        }
        for entry in feed["entries"]
    }
    torrents = dict(
        filter(
            lambda torrent: config["CHDBits"]["size"][0]
            <= torrent[1]["size"]
            <= config["CHDBits"]["size"][1]
            and re.search(config["CHDBits"]["regexp"], torrent[1]["title"]) != None,
            torrents.items(),
        )
    )
    for web in config["CHDBits"]["web"]:
        response = requests.get(
            web,
            headers={"user-agent": config["CHDBits"]["user_agent"]},
            cookies=config["CHDBits"]["cookies"],
            proxies=config["CHDBits"]["proxies"],
            timeout=config["CHDBits"]["web_timeout"],
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "lxml")
            rows = soup.find("table", class_="torrents").find_all("tr", recursive=False)
            if rows == []:
                raise Exception
            for row in rows[1:]:
                cols = row.find_all("td", recursive=False)
                if len(cols) >= 10:
                    id = re.search("id=(\d+)", str(cols[1])).group(1)
                    if id in torrents:
                        web_info = {
                            "free": False,
                            "free_end": None,
                            "hr": None,
                            "downloaded": False,
                            "seeder": -1,
                            "leecher": -1,
                            "snatch": -1,
                        }
                        if re.search('class="pro_\S*free', str(cols[1])) != None:
                            web_info["free"] = True
                            free_end = re.search('<span title="(.+?)"', str(cols[1]))
                            web_info["free_end"] = (
                                None
                                if free_end == None
                                else time.mktime(
                                    time.strptime(
                                        free_end.group(1), "%Y-%m-%d %H:%M:%S"
                                    )
                                )
                                - time.timezone
                                - config["CHDBits"]["timezone"] * 3600
                            )
                        hr = cols[1].find("div", class_="circle-text")
                        if hr != None:
                            web_info["hr"] = int(re.sub("\D", "", hr.text)) * 86400
                        web_info["seeder"] = int(re.sub("\D", "", cols[5].text))
                        web_info["leecher"] = int(re.sub("\D", "", cols[6].text))
                        web_info["snatch"] = int(re.sub("\D", "", cols[7].text))
                        if re.search("\d", cols[9].text) != None:
                            web_info["downloaded"] = True
                        torrents[id] = dict(torrents[id], **web_info)
        else:
            raise Exception
        time.sleep(1)
    return {
        "[CHDBits]" + id: torrent
        for id, torrent in torrents.items()
        if "downloaded" in torrent
    }
