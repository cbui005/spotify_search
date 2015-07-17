# Spotify_Search Reddit Bot
# Author: Calvin Bui
# github.com/cbui005
import praw
import datetime
import traceback
import spotipy
from time import sleep
from collections import deque

# config. could use config file and import info over
USERNAME = 'fill_in_reddit_username (spotify_search)'
PASSWORD = 'fill_in_reddit_password (password)'
USER_AGENT = '#spotify_search'
REQUEST_LIMIT = 10
SLEEP_TIME = 30
CACHE_SIZE = 200
SUBREDDIT = 'music'


def main():
    print('Spotify_Search v1.0 by Calvin Bui')
    # login to reddit
    r = praw.Reddit(user_agent=USER_AGENT)
    r.login(USERNAME, PASSWORD, disable_warning=True)

    # Set up our cache and completed work set
    cache = deque(maxlen=CACHE_SIZE)  # double-ended queue
    already_done = set()

    # Setup subreddits
    comments = praw.helpers.comment_stream(r, SUBREDDIT, limit=None)
    print('Looking at /r/' + SUBREDDIT)

    #correct_info is flag for detecting what type of comment it is
    correct_info = False
    running = True
    while running:
        try:
            # Check comments
            for c in comments:
                # Did we recently check it? If so fetch new comments
                if c.id in cache:
                    break
                # Add this to our cache
                cache.append(c.id)
                # Check if we need to reply
                if check_comment(c.body):
                    # Check if we already replied
                    for reply in c.replies:
                        if reply.author.name == USERNAME:
                            already_done.add(c.id)
                    if c.id not in already_done:
                        bodysplit = c.body.lower().split('\n\n')
                        if len(bodysplit) <= REQUEST_LIMIT:
                            text = ''
                            for line in bodysplit:
                                if check_comment(line):
                                    # handles if both 'song:' and 'artist:' are specified
                                    if 'song:' in line.lower() and (correct_info == False):
                                        # handles if user provided both song and artist
                                        if 'artist:' in line.lower():
                                            text = parse_song_artist(line)
                                            artist_loc = text.find('artist:')
                                            song_loc = text.find('song:')
                                            song = ''
                                            artist = ''
                                            if artist_loc < song_loc:
                                                artist = text[8:song_loc - 1]
                                                song = text[song_loc + 6:len(text)]
                                            elif song_loc < artist_loc:
                                                song = text[6:artist_loc - 1]
                                                artist = text[artist_loc + 8:len(text)]
                                            spotify_pair_search(song, artist, c, already_done)
                                            correct_info = True
                                        # handles if only 'song:' is found in the comment
                                        else:
                                            song = parse_name(line, 'song:')
                                            correct_info = True
                                            print("found song: " + song)
                                            spotify_song_search(song, c, already_done)

                                    # handles if only 'artist:' is found in the comment
                                    elif 'artist:' in line.lower() and (correct_info == False):
                                        artist = parse_name(line, 'artist:')
                                        correct_info = True
                                        print("found artist: " + artist)
                                        spotify_artist_search(artist, c, already_done)
                                    # handles if could not find 'artist:' or 'song:' in comment
                                    else:
                                        text = 'Could not recognize comment format.\n\n'
                                        text = add_signature(text)
                                        print(text)
                                        replyto(c, text, already_done)
                                    correct_info = False


        except KeyboardInterrupt:
            running = False
        except Exception as e:
            now = datetime.datetime.now()
            print(now.strftime("%m-%d-%Y %H:%M"))
            print(traceback.format_exc())
            print('ERROR:', e)
            print('Going to sleep for 30 seconds...\n')
            sleep(SLEEP_TIME)
            continue
    print("finish")


# checks a comment for required text
def check_comment(text):
    if '/u/spotify_search' in text.lower():
        return True
    return False

# parses artist name from comment
def parse_song_artist(line):
    text = line.lower()
    begin = text.find('/u/spotify_search ')
    text = text[begin + 18:]

    # check for spaces in the front or back
    if text[0] == ' ':
        text = text[1:]
    if text[len(text) - 1] == ' ':
        text = text[0:len(text) - 1]
    return text


# parses text from bot's username call
def parse_name(line, phrase):
    text = line.lower()
    begin = text.find('/u/spotify_search ' + phrase) + len('/u/spotify_search ' + phrase)
    text = text[begin:]

    # check for spaces in the front or back
    if text[0] == ' ':
        text = text[1:]
    if text[len(text) - 1] == ' ':
        text = text[0:len(text) - 1]
    return text

# given artist name and song, build a list and call function to reply
def spotify_pair_search(song, artist, c, already_done):
    sp = spotipy.Spotify()
    results = sp.search(q=song, limit=None)
    string_results = str(results)

    # test if song is valid (if total: 0, then invalid)
    begin = string_results.find("'total':")
    total = string_results[begin + 9:begin + 11]

    # check if total was single or double digit
    if total[1] == ',' or total[1] == '}':
        total = total[0]

    # if total was 0, artist name was most likely misspelled, print error
    if total == '0':
        print("Could not find a song: " + song + ' by ' + artist + "'.")
        song_link = []
        song_name = []
        #assemble text string to use PRAW's reply function
        assemblesonglist(song_link, song_name, artist, song, c, already_done)
    else:
        song_link = []
        song_name = []

        for i, t in enumerate(results['tracks']['items']):
            link_str = str(t['external_urls'])
            artist_str = str(t['artists'])
            begin = artist_str.find("'name':")
            begin_str = artist_str[begin:]
            end = begin_str.find(',')
            artist_name = str(begin_str[9:end - 1])
            if artist_name.lower() == artist.lower():
                song_name.append(t['name'])
                song_link.append(link_str[13:len(link_str) - 2])
        #assemble text string to use PRAW's reply function
        assemblesong(song_link, song_name, artist, song, c, already_done)

# given song name, build a list of results and call function to reply
def spotify_song_search(text, c, already_done):
    sp = spotipy.Spotify()
    result = sp.search(q=text, limit=None, offset=0, type='track')
    string_result = str(result)
    # test if song is valid (if total: 0, then invalid)
    begin = string_result.find("'total':")
    total = string_result[begin + 9:begin + 11]
    # check if total was single or double digit
    if total[1] == ',' or total[1] == '}':
        total = total[0]
    # if total was 0, artist name was most likely misspelled, print error
    if total == '0':
        print("Could not find a song on Spotify named '" + fix_caps(text) + "'.")
        song_link = []
        song_name = []
        artist = []
        #assemble text string to use PRAW's reply function
        assemblesonglist(song_link, song_name, artist, text, c, already_done)
    else:
        # store values into appropriate lists
        song_link = []
        song_name = []
        artist = []
        for i, t, in enumerate(result['tracks']['items']):
            link_str = str(t['external_urls'])
            song_name.append(t['name'])
            song_link.append(link_str[13:len(link_str) - 2])
            artist_str = str(t['artists'])
            begin = artist_str.find("'name':")
            begin_str = artist_str[begin:]
            end = begin_str.find(',')
            artist_name = begin_str[9:end - 1]
            artist.append(artist_name)
        #assemble text string to use PRAW's reply function
        assemblesonglist(song_link, song_name, artist, text, c, already_done)

# given an artist name, build a list of artists' top songs and call function to reply
def spotify_artist_search(text, c, already_done):
    sp = spotipy.Spotify()
    result = sp.search(q=text, limit=None, offset=0, type='artist')
    string_result = str(result)
    # test if artist is valid (total: 0)
    begin = string_result.find("'total':")
    total = string_result[begin + 9:begin + 11]
    # check if total was single or double digit
    if total[1] == ',' or total[1] == '}':
        total = total[0]
    # if total was 0, artist name was most likely misspelled, print error
    if total == '0':
        print("Could not find an artist on Spotify named '" + text + "'.")
        song_link = []
        song_name = []
        #assemble text string to use PRAW's reply function
        assembletextartist(song_link, song_name, text, c, already_done)

    else:
        # get artist uri
        artist_uri = string_result.find("'spotify:artist:")
        urn = string_result[artist_uri + 1:artist_uri + 38]
        # get artists top tracks and spotify links to them
        response = sp.artist_top_tracks(urn)
        song_link = []
        song_name = []
        for track in response['tracks']:
            link_str = str(track['external_urls'])
            song_link.append(str(link_str[13:len(link_str) - 2]))
            song_name.append(track['name'])
        #assemble text string to use PRAW's reply function
        assembletextartist(song_link, song_name, text, c, already_done)

# concatenate strings to form reddit friendly comment
def assemblesong(song_link, song_name, artist, song, c, already_done):
    if not song_link:
        text = "Could not find a song on Spotify named '" + fix_caps(song) + "' by " + fix_caps(artist) + '.'
        text = add_signature(text)
        print(text)
        #call to PRAW's reply function
        replyto(c, text, already_done)
    else:
        text = ('Results for: ' + song + ' by ' + fix_caps(artist) + '\n\n')
        for i in range(len(song_name)):
            text += '[' + str(song_name[i]) + '](' + str(song_link[i]) + ') by ' + fix_caps(artist) + '\n\n'
        text = add_signature(text)
        print(text)
        #call to PRAW's reply function
        replyto(c, text, already_done)


# concatenate strings to form reddit friendly comment
def assemblesonglist(song_link, song_name, artist, text, c, already_done):
    if not song_link:
        text = "Could not find a song: '" + fix_caps(text) + "'."
        text = add_signature(text)
        print(text)
        #call to PRAW's reply function
        replyto(c, text, already_done)
    else:
        text2 = "Top Results for '" + fix_caps(text) + "':\n\n"
        text = text2
        for i in range(len(song_name)):
            text += '[' + str(song_name[i]) + '](' + str(song_link[i]) + ') by ' + artist[i] + '\n\n'
        text = add_signature(text)
        print(text)
        #call to PRAW's reply function
        replyto(c, text, already_done)


# concatenate strings to form reddit friendly comment
def assembletextartist(song_link, song_name, text, c, already_done):
    if not song_link:
        text = "Could not find artist '" + fix_caps(text) + "'."
        text = add_signature(text)
        print(text)
        #call to PRAW's reply function
        replyto(c, text, already_done)
    else:
        text = fix_caps(text)
        text += "'s Top Songs:\n\n"
        for i in range(len(song_name)):
            text += '[' + str(song_name[i]) + '](' + str(song_link[i]) + ')\n\n'
        text = add_signature(text)
        print(text)
        #call to PRAW's reply function
        replyto(c, text, already_done)


# add signature to end of post
def add_signature(text):
    text += '\n\n***\n\n'
    text += '[How to use Spotify_Search.](https://github.com/cbui005)\n\n'
    text += '*Note: Titles or names must match exactly, but capitalization does not matter.*\n\n'
    text += "PM for Feedback | [Source Code](https://github.com/cbui005) | This bot uses the [Spotipy](https://developer.spotify.com/web-api/) api."
    return text


# replies to given comment
def replyto(c, text, done):
    now = datetime.datetime.now()
    print(len(done) + 1), 'ID:', c.id, 'Author:', c.author.name, 'r/' + str(
        c.subreddit.display_name), 'Title:', c.submission.title
    print(now.strftime("%m-%d-%Y %H:%M"), '\n')
    c.reply(text)
    done.add(c.id)


# fix capitalization
def fix_caps(string):
    ans = string[0].upper()
    for i in range(1, len(string), 1):
        if string[i - 1] == ' ':
            ans += string[i].upper()
        else:
            ans += string[i]
    return ans


main()
