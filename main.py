import os
from dotenv import load_dotenv
from flask import Flask, session, url_for, redirect, request, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

# Load environment variables from .env file
load_dotenv()

app=Flask(__name__)

#secret key for session management
app.config['SECRET_KEY'] = os.urandom(64)

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri =  os.getenv('REDIRECT_URI')
scope = scope = 'playlist-read-private playlist-modify-private playlist-modify-public'


# store the access token in the session
cache_handler = FlaskSessionCacheHandler(session)

# Initialize SpotifyOAuth with the necessary credentials
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True)

def isromantic(features):
    return(
    0.4<=features['valence']<=0.8 and
    0.2<=features['energy']<=0.6 and
    0.3<=features['danceability']<=0.6
    )

def ishappy(features):
    return(
    0.7<=features['valence']<=1.0 and
    0.5<=features['energy']<=1.0 and
    0.5<=features['danceability']<=1.0
    )

def issad(features):
    return(
    0.0<=features['valence']<=0.3 and
    0.2<=features['energy']<=0.6 and
    0.3<=features['danceability']<=0.4
    )

# Create a Spotify client instance
sp= Spotify(auth_manager=sp_oauth)

@app.route('/')
def home():
    #check if the user is already logged in
    token_info=cache_handler.get_cached_token()
    if not token_info:
        auth_url=sp_oauth.get_authorize_url()
        return f'<a href={auth_url}>Click here to log in with spotify</a>'
    return render_template('details.html')

@app.route('/details', methods=["GET", "POST"])
def details():
    mood=""
    artists=[]
    song_no=50
    if request.method=="POST":
        mood=request.form.get("mood")
        artist_names=request.form.get("artists")
        artists_list=artist_names.split(",")
        artists=[artist.strip() for artist in artists_list]
        song_no=int(request.form.get("song_no"))
        #no of songs by the specified artists to add to the playlist
        artist_songs_int=int((song_no/  2)/len(artists))
    print(artists)

    top_track_ids=[]
    selected_songs=[]

    #getting the track ids
    for artist in artists:
        results = sp.search(q=f'artist:"{artist}"', type='artist')
        artist_items=results['artists']['items']
        if artist_items:
            artist_id=results['artists']['items'][0]['id']
            top_tracks=sp.artist_top_tracks(artist_id)['tracks']
            top_track_ids.extend([track['uri'] for track in top_tracks])
        else:
            print(f"No results found for artist: {artist}")
    def get_features(track_id):
        features = sp.audio_features(track_id)[0]
        return features
    #adding the songs
    if mood=="romantic":
        selected_songs.extend([song for song in top_track_ids if isromantic(get_features(song))])
    elif mood=="happy":
        selected_songs.extend([song for song in top_track_ids if ishappy(get_features(song))])
    elif mood=="sad":
        selected_songs.extend([song for song in top_track_ids if isromantic(get_features(song))])
    else:
        pass
    
    if len(selected_songs)<song_no:
        selected_songs=selected_songs[:song_no]
    elif len(selected_songs)==song_no:
        pass
    else:
        #get recommendations to fill in whatever number is left
        n=song_no-len(selected_songs)
        if mood=="romantic":
            recommendations = sp.recommendations(
                seed_genres=['r-n-b', 'soul', 'afrobeat'],
                limit=n,
                min_valence=0.4,
                max_valence=0.8,
                min_energy=0.2,
                max_energy=0.6,
                min_danceability=0.3,
                max_danceability=0.6)
            tracks=recommendations['tracks']
            selected_songs.extend([track for track in tracks])
        elif mood=="happy":
            recommendations = sp.recommendations(
                seed_genres=['techno', 'pop', 'hiphop'],
                limit=n,
                min_valence=0.7,
                max_valence=1,
                min_energy=0.6,
                max_energy=1,
                min_danceability=0.6,
                max_danceability=1)
            tracks=recommendations['tracks']
            selected_songs.extend([track for track in tracks])
        elif mood=="sad":
            recommendations = sp.recommendations(
                seed_genres=['sad', 'emo'],
                limit=n,
                min_valence=0,
                max_valence=0.4,
                min_energy=0,
                max_energy=0.5,
                min_danceability=0,
                max_danceability=0.3)
            tracks=recommendations['tracks']
            selected_songs.extend([track for track in tracks])
    
    print(selected_songs)
    

    return render_template("details.html")

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code']) #refreshes the access code
    return redirect(url_for('details'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__=='__main__':
    app.run(host='0.0.0.0', debug=True)
