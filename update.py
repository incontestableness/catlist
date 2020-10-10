#!/usr/bin/env python3

import argparse
import json
import os
import pprint
import re
import time



parser = argparse.ArgumentParser()
parser.add_argument("--live-scrape", action="store_true") # auto-update the playerlist periodically
parser.add_argument("--playerlist-only", action="store_true") # just rewrite the playerlist based on the current database
parser.add_argument("--check", action="store_true") # open each new entry in the browser for viewing
parser.add_argument("--commit", action="store_true") # commit database/playerlist changes
parser.add_argument("--push", action="store_true") # automatically push the changes after updating
args = parser.parse_args()


# Load bot steamid database
file = open("catlist.nsv", "r")
data = file.read()
file.close()
database = data.split("\n")
database.remove("")

# Load steamid exclusion database
file = open("excludes.nsv", "r")
data = file.read()
file.close()
excludes = data.split("\n")
excludes.remove("")


def generate_playerlist():
	# Compile the json
	data = {"$schema": "https://raw.githubusercontent.com/PazerOP/tf2_bot_detector/master/schemas/v3/playerlist.schema.json"}
	data["file_info"] = {
			     "authors": ["The Great Milenko"],
			     "description": "List of automatically detected cathook users",
			     "title": "Milenko's cathook list",
			     "update_url": "https://incontestableness.github.io/milenko/playerlist.milenko-list.json"
	}

	playerlist = []
	for entry in database:
		playerlist.append({
			"steamid": f"[U:1:{entry}]",
			"attributes": ["cheater"],
		})

	data["players"] = playerlist

	# Write the json
	file = open("playerlist.milenko-list.json", "w")
	file.write(json.dumps(data, indent=4))
	file.close()


def update_db(entry_list):
	new_entries = []
	for entry in entry_list:
		if entry == "0": # invalid steamid
			continue
		if entry in excludes: # ignore whitelisted steamids
			continue
		if entry not in database: # don't add duplicates
			database.append(entry)
			new_entries.append(entry)

	# Check new steamids
	if args.check:
		for entry in new_entries:
			os.system(f"~/Desktop/Firefox-Developer-Edition/firefox https://steamid.xyz/{entry}")

	# Write updated database to file
	os.remove("catlist.nsv")
	file = open("catlist.nsv", "a")
	database.sort()
	for entry in database:
		file.write(f"{entry}\n")
	file.close()

	# Copy updated database so bots can use it
	os.system("cp -v catlist.nsv /opt/cathook/data/")

	# Re-generate the playerlist
	generate_playerlist()

	message = f"Added {len(new_entries)} entries. There are now {len(database)} entries."
	print(message)
	return message


# Scrapes all logs for new bot steamids
# Used in live-scrape mode to auto-update the playerlist periodically without manually dumping the plist
def scrape():
	live_entries = []

	filenames = os.listdir("/tmp")
	bot_regex = re.compile("cathook-[a-z][-a-z0-9_]{11}-[0-9][0-9]?-[0-9]*.log")
	user_regex = re.compile("cathook-[a-z]{4}-[0-9]*.log")
	for fname in filenames:
		if bot_regex.match(fname) or user_regex.match(fname):
			print(f"Reading /tmp/{fname}")
			file = open(f"/tmp/{fname}", "r", encoding="ISO-8859-1")
			data = file.read()
			file.close()

			data = data.split("\n")
			for line in data:
				try:
					entry = line.split("NEW bot steamid entry: ")[1]
					if entry not in live_entries: # might as well de-duplicate here
						live_entries.append(entry)
				except: # not an entry log line
					pass
	return live_entries


def commit(message):
	if args.commit:
		print("Committing database/playerlist changes")
		os.system("git add catlist.nsv playerlist.milenko-list.json")
		os.system(f"git commit -m \"{message}\"")
	else:
		print("Note: not committing")


def push():
	if args.push:
		print("Pushing to repo")
		os.system("git push")
	else:
		print("Note: not pushing")


if args.live_scrape:
	while True:
		live_entries = scrape()
		message = update_db(live_entries)
		commit(message)
		push()
		time.sleep(60) # update every minute
elif args.playerlist_only:
	update_db([])
	commit("Update the playerlist")
else:
	entry_list = scrape()
	message = update_db(entry_list)
	commit(message)
	push()
