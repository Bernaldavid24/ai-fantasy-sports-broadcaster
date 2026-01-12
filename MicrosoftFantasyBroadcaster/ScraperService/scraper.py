import json
import pika
import os
import math
import random
from pathlib import Path
from espn_api.football import League
from dotenv import load_dotenv
from openai import AzureOpenAI
from storyline_generator import StorylineGenerator

# --- 1. ROBUST ENV LOADING ---
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- 2. CONFIGURATION ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
LEAGUE_ID = int(os.getenv('ESPN_LEAGUE_ID', '0'))
YEAR = int(os.getenv('ESPN_YEAR', '2025'))
ESPN_S2 = os.getenv('ESPN_S2')
SWID = os.getenv('ESPN_SWID')
QUEUE_NAME = 'game_stats_queue'

# Azure Config
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_DEPLOYMENT = os.getenv('AZURE_DEPLOYMENT_NAME')

# --- 3. BROADCAST DIRECTOR (Matt & Jose Edition) ---
class BroadcastDirector:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_KEY,
            api_version="2024-05-01-preview"
        )

    def generate_intro(self, week):
        prompt = (
            f"Write a TV intro for the Week {week} Fantasy Recap with hosts MATT and JOSE.\n"
            f"Roles:\n"
            f"- MATT: High energy, professional host. Welcomes everyone.\n"
            f"- JOSE: The color commentator. He is hyped and ready to roast people.\n"
            f"Rules:\n"
            f"- They MUST refer to each other by name.\n"
            f"- Format: [MATT]: ... [JOSE]: ...\n"
            f"- Keep it under 4 lines."
        )
        return self._call_ai(prompt, fallback="[MATT]: Welcome to Week " + str(week) + "! [JOSE]: Let's go Matt, I'm ready!")

    def generate_transition(self, home_team, away_team):
        prompt = (
            f"Write a transition to the {home_team} vs {away_team} game.\n"
            f"Matt sets it up, Jose adds a quick hype comment.\n"
            f"Format: [MATT]: ... [JOSE]: ..."
        )
        return self._call_ai(prompt, fallback=f"[MATT]: Next up, {home_team} vs {away_team}. [JOSE]: This one was ugly!")

    def generate_banter_recap(self, recap_text, winner, score):
        # This takes the dry stats recap and turns it into a conversation
        prompt = (
            f"Rewrite this recap into a dialogue between MATT and JOSE:\n"
            f"'{recap_text}'\n\n"
            f"Roles:\n"
            f"- MATT (60% of text): Reads the actual stats and play-by-play.\n"
            f"- JOSE (40% of text): Reacts, makes fun of the loser, or praises the winner. He interrupts Matt.\n"
            f"Rules:\n"
            f"- Use tags [MATT]: and [JOSE]:\n"
            f"- Make them talk TO each other. (e.g., 'Did you see that, Jose?', 'Tell em, Matt!')\n"
            f"- Keep it under 6 lines total."
        )
        return self._call_ai(prompt, fallback=f"[MATT]: {winner} won with {score} points. [JOSE]: Total domination!")

    def generate_outro(self, week):
        prompt = (
            f"Write a sign-off for Week {week}.\n"
            f"Matt wraps it up professionally, Jose yells something funny or tells people to hit the waiver wire.\n"
            f"Format: [MATT]: ... [JOSE]: ..."
        )
        return self._call_ai(prompt, fallback="[MATT]: That's the show! [JOSE]: Peace out!")

    def _call_ai(self, prompt, fallback):
        try:
            response = self.client.chat.completions.create(
                model=AZURE_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a scriptwriter for 'The Fantasy Zone'. Hosts: Matt (Pro) and Jose (Wild). They have great chemistry and banter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=1.0, 
                max_tokens=250
            )
            content = response.choices[0].message.content
            if content: return content.strip()
            return fallback
        except Exception as e:
            print(f"   ⚠️ Director Error: {e}")
            return fallback

class StatsAnalyzer:
    def get_player_performances(self, matchup):
        players = {'home': [], 'away': []}
        if hasattr(matchup, 'home_lineup'):
            for player in matchup.home_lineup:
                if player.slot_position != 'BE':
                    players['home'].append(self._extract_stats(player))
        if hasattr(matchup, 'away_lineup'):
            for player in matchup.away_lineup:
                if player.slot_position != 'BE':
                    players['away'].append(self._extract_stats(player))
        return players

    def _extract_stats(self, player):
        raw_stats = player.stats.get(player.lineupSlot, {})
        if not raw_stats:
             keys = list(player.stats.keys())
             if keys: raw_stats = player.stats[keys[0]]
        return {
            'name': player.name, 'position': player.position,
            'points': player.points, 'stats': raw_stats 
        }

    def find_interesting_performances(self, players_dict):
        notable = []
        for team in ['home', 'away']:
            for player in players_dict[team]:
                stats = player['stats']
                position = player['position']
                name = player['name']
                points = player['points']
                
                if position == 'QB':
                    pass_yds = stats.get('passingYards', 0)
                    pass_tds = stats.get('passingTouchdowns', 0)
                    if pass_yds >= 350: notable.append(f"🚀 {name}: {pass_yds} passing yards!")
                    if pass_tds >= 4: notable.append(f"🎯 {name}: {pass_tds} passing TDs!")
                elif position == 'RB':
                    total_tds = stats.get('rushingTouchdowns', 0) + stats.get('receivingTouchdowns', 0)
                    rush_yds = stats.get('rushingYards', 0)
                    if total_tds >= 2: notable.append(f"🔥 {name}: {total_tds} total TDs!")
                    if rush_yds >= 100: notable.append(f"💯 {name}: {rush_yds} rushing yards!")
                elif position in ['WR', 'TE']:
                    rec_tds = stats.get('receivingTouchdowns', 0)
                    rec_yds = stats.get('receivingYards', 0)
                    if rec_tds >= 2: notable.append(f"🎯 {name}: {rec_tds} receiving TDs!")
                    if rec_yds >= 100: notable.append(f"💯 {name}: {rec_yds} receiving yards!")
                
                if points >= 30: notable.append(f"🌟 {name}: MONSTER game ({points} pts)!")
        return notable

    def find_matchup_storylines(self, matchup, players_dict):
        storylines = []
        home_score = matchup.home_score
        away_score = matchup.away_score
        diff = abs(home_score - away_score)
        
        winner = matchup.home_team.team_name if home_score > away_score else matchup.away_team.team_name
        if diff >= 40: storylines.append(f"💣 BLOWOUT! {winner} dominates by {diff:.1f} points!")
        elif diff <= 5: storylines.append(f"😰 NAIL-BITER! Just {diff:.1f} points separate them!")
        if home_score >= 150: storylines.append(f"🔥 {matchup.home_team.team_name}: MONSTER SCORE ({home_score} pts)!")
        if away_score >= 150: storylines.append(f"🔥 {matchup.away_team.team_name}: MONSTER SCORE ({away_score} pts)!")
        return storylines

def main():
    if LEAGUE_ID == 0:
        print("❌ ERROR: ESPN_LEAGUE_ID not found. Check your .env file.")
        return

    print(f"🏈 Connecting to League {LEAGUE_ID}...")
    try:
        league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)
    except Exception as e:
        print(f"❌ Failed to connect to ESPN: {e}")
        return

    analyzer = StatsAnalyzer()
    director = BroadcastDirector()
    
    print("🤖 Initializing Azure AI Storyline Generator...")
    try:
        story_gen = StorylineGenerator()
        ai_enabled = True
    except ValueError as e:
        print(f"⚠️ AI Generator Error: {e}")
        ai_enabled = False
        story_gen = None

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME)
    except Exception as e:
        print(f"❌ RabbitMQ Error: {e}")
        return
    
    current_week = league.current_week
    if current_week == 0: current_week = 1

    print(f"📊 Processing weeks 1-{current_week}...")
    
    for week in range(1, current_week + 1):
        try:
            box_scores = league.box_scores(week)
        except Exception as e:
            print(f"⚠️ Could not fetch Week {week}: {e}")
            continue

        # --- RANK GAMES ---
        game_rankings = []
        for game in box_scores:
            if isinstance(game.home_team, int) or isinstance(game.away_team, int): continue
            excitement_score = (game.home_score + game.away_score) + (100 - abs(game.home_score - game.away_score))
            game_rankings.append({'game': game, 'score': excitement_score})
        
        game_rankings.sort(key=lambda x: x['score'], reverse=True)
        feature_games = [g['game'] for g in game_rankings[:3]]
        quick_games = [g['game'] for g in game_rankings[3:]]

        # --- GENERATE SCRIPT ---
        print(f"🎬 Director generating Matt & Jose script for Week {week}...")
        
        # Intro
        script = director.generate_intro(week) + "\n"
        
        games_processed = 0

        # Feature Games
        for game in feature_games:
            players_dict = analyzer.get_player_performances(game)
            notable_perfs = analyzer.find_interesting_performances(players_dict)
            matchup_stories = analyzer.find_matchup_storylines(game, players_dict)
            
            if ai_enabled and story_gen:
                stats_payload = {
                    'team_1': {'team_name': game.home_team.team_name, 'score': game.home_score},
                    'team_2': {'team_name': game.away_team.team_name, 'score': game.away_score}
                }
                
                print(f"   🌟 FEATURE: {game.home_team.team_name} vs {game.away_team.team_name}...")
                try:
                    # 1. Transition
                    transition = director.generate_transition(game.home_team.team_name, game.away_team.team_name)
                    script += f"{transition}\n"

                    # 2. Get the "Facts" from the Story Generator
                    raw_story = story_gen.generate_storyline(stats=stats_payload, players=players_dict, notable_performances=notable_perfs, storylines=matchup_stories, records=[])
                    
                    if raw_story:
                        # 3. Convert Facts into Banter
                        winner_name = game.home_team.team_name if game.home_score > game.away_score else game.away_team.team_name
                        winner_score = max(game.home_score, game.away_score)
                        
                        banter = director.generate_banter_recap(raw_story, winner_name, winner_score)
                        script += f"{banter}\n"
                        games_processed += 1

                except Exception as e:
                    print(f"   ❌ AI Gen Error: {e}")

        # Quick Games (Matt reads these alone quickly)
        if quick_games:
            script += "[MATT]: AND IN OTHER ACTION AROUND THE LEAGUE...\n"
            for game in quick_games:
                winner = game.home_team.team_name if game.home_score > game.away_score else game.away_team.team_name
                loser = game.away_team.team_name if game.home_score > game.away_score else game.home_team.team_name
                script += f"[MATT]: {winner} defeated {loser}, {max(game.home_score, game.away_score)} to {min(game.home_score, game.away_score)}.\n"
                games_processed += 1

        # Outro
        script += director.generate_outro(week)
        
        if games_processed > 0:
            message = {
                "week": week,
                "shortName": f"Week_{week}_Full_Recap",
                "home_team": "Recap", "home_score": 0, "home_roster": [],
                "away_team": "Recap", "away_score": 0, "away_roster": [],
                "storylines": [],
                "ai_recap": script
            }
            channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=json.dumps(message))
            print(f" [x] Sent Matt & Jose Script for Week {week}")
        else:
            print(f" [!] Skipping Week {week} message (No games processed).")

    connection.close()

if __name__ == "__main__":
    main()