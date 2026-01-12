import os
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables from the .env file in the ScraperService folder
load_dotenv()

class StorylineGenerator:
    """
    Generates entertaining storylines using Azure OpenAI.
    Migrated from Claude (Anthropic) to Microsoft Azure for the Fantasy Broadcaster project.
    """
    
    def __init__(self):
        """
        Initialize the Azure OpenAI client using credentials from .env
        """
        # Validate that keys exist to prevent confusing errors later
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_DEPLOYMENT_NAME")

        if not api_key or not endpoint or not deployment:
             raise ValueError("❌ Missing Azure configuration! Check your .env file for AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_DEPLOYMENT_NAME.")

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-15-preview",  # Use a stable version suitable for your region
            azure_endpoint=endpoint
        )
        self.deployment_name = deployment
        
        print(f"✅ Storyline Generator initialized (Azure Deployment: {self.deployment_name})")

    def format_stats_for_prompt(self, stats, players, notable_performances, storylines, records):
        """
        Format all the stats data into a structured prompt.
        
        CRITICAL: This function preserves the specific "Trash Talk" personality 
        from the original project. Do not modify the prompt text without testing.
        """
        
        # Determine winner and loser for trash talk purposes
        # Note: Adjust keys ('team_1', 'score') if your scraper output structure changes
        if stats['team_1']['score'] > stats['team_2']['score']:
            winner_name = stats['team_1']['team_name']
            winner_score = stats['team_1']['score']
            loser_name = stats['team_2']['team_name']
            loser_score = stats['team_2']['score']
        else:
            winner_name = stats['team_2']['team_name']
            winner_score = stats['team_2']['score']
            loser_name = stats['team_1']['team_name']
            loser_score = stats['team_1']['score']
            
        margin = abs(stats['team_1']['score'] - stats['team_2']['score'])
        
        # --- BEGIN PROMPT CONSTRUCTION ---
        prompt = f"""You are a fantasy football analyst writing entertaining weekly recaps. Think Pat McAfee Show or Stephen A. Smith energy - ANIMATED, OPINIONATED, and FUN!

THE MATCHUP:
{winner_name}: {winner_score:.1f} points (WINNER)
{loser_name}: {loser_score:.1f} points (LOSER)
Beatdown Margin: {margin:.1f} points

"""
        
        # Add notable individual performances
        if notable_performances:
            prompt += "PLAYERS WHO SHOWED UP:\n"
            for performance in notable_performances:
                # Clean up emojis if they exist in the raw data, though the prompt likes energy
                clean_perf = performance.lstrip('🔥💯🚀🎯⚡💪🏃📡🎣🌟💥📈🛡️📊🦵💣🤯🏆🔒')
                prompt += f"- {clean_perf}\n"
            prompt += "\n"
        
        # Add matchup storylines
        if storylines:
            prompt += "THE REAL STORY:\n"
            for storyline in storylines:
                clean_story = storyline.lstrip('💣😰🔥😬🎒')
                prompt += f"- {clean_story}\n"
            prompt += "\n"
        
        # Add broken records
        if records:
            prompt += "🚨 RECORDS SHATTERED:\n"
            for record in records:
                prompt += f"- {record}\n"
            prompt += "\n"
        
        # The Personality Instructions (Preserved EXACTLY from original)
        prompt += f"""
Write a 3-4 paragraph recap that sounds like you're calling this game on a sports talk show. 

MANDATORY STYLE RULES:
❌ NO formal sports journalism language
❌ NO "this writer thinks" or "one could argue"  
❌ NO boring, neutral descriptions
✅ USE casual language like you're talking to your fantasy league group chat
✅ USE trash talk (roast the losing team!)
✅ USE hype (celebrate the winning team's dominance!)
✅ USE rhetorical questions for effect
✅ USE present tense for more energy ("Mahomes TORCHES the defense" not "Mahomes torched")

TONE EXAMPLES:
- "Are you KIDDING me right now?!"
- "This wasn't a matchup, this was a CLINIC"
- "Someone check on [loser's team], they might need therapy after this"
- "Let's talk about [player name] for a second - ABSOLUTELY UNCONSCIOUS"
- "If you started [player], you're eating GOOD this week"

STRUCTURE:
Paragraph 1: Open with the VIBE of the game (blowout? nail-biter? upset?). Make it dramatic. Winner gets hyped, loser gets roasted (friendly but spicy).

Paragraph 2-3: Spotlight 2-3 key performances. Use specific stats. Build the narrative - who was the MVP? Who disappeared? Any unexpected heroes or brutal busts?

Paragraph 4: Close with either:
- A final zinger at the loser
- Props to an insane individual performance  
- Forward-looking trash talk ("Good luck next week, {loser_name}")
- Or if records were broken, END on that hype

LANGUAGE STYLE:
- Short, punchy sentences mixed with longer ones
- Contractions (wasn't, didn't, can't)
- Slang is ENCOURAGED (cooking, eating, bodied, torched, etc.)
- All caps for EMPHASIS on key moments
- Sentence fragments. Are fine. For effect.

DO NOT:
- Use asterisks or markdown formatting
- Write in past tense throughout (mix it up with present tense for energy)
- Be neutral or boring
- Apologize or hedge ("perhaps", "maybe", "might have")

Remember: The goal is ENTERTAINMENT. Make the winner feel like champions and the loser laugh at themselves!
"""
        return prompt

    def generate_storyline(self, stats, players=None, notable_performances=None, storylines=None, records=None):
        """
        Generate a storyline by calling the Azure OpenAI API.
        """
        # Handle empty lists if None is passed
        players = players or {}
        notable_performances = notable_performances or []
        storylines = storylines or []
        records = records or []

        # 1. Build the prompt
        prompt = self.format_stats_for_prompt(
            stats, players, notable_performances, storylines, records
        )
        
        print(f"🤖 Generating storyline for {stats['team_1']['team_name']} vs {stats['team_2']['team_name']}...")
        
        try:
            # 2. Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name, # Critical: Matches the "Deployment Name" in Azure Portal
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.8 # High creativity for trash talk
            )
            
            # 3. Extract text
            storyline = response.choices[0].message.content
            print("✅ Storyline generated successfully!")
            return storyline
            
        except Exception as e:
            print(f"❌ Azure API Error: {e}")
            return None

    def save_storyline(self, storyline, week, matchup_info):
        """
        Save the generated storyline to the data folder.
        """
        # Adjust path to match ScraperService structure
        # Assuming we want to save in a 'data' folder relative to this script
        output_dir = os.path.join(os.path.dirname(__file__), "data", "storylines")
        os.makedirs(output_dir, exist_ok=True)
        
        safe_matchup = matchup_info.replace(" ", "_").replace("/", "-")
        filename = f"week_{week}_{safe_matchup}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Week {week} Matchup Recap (Azure Generated)\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            f.write(storyline)
            
        print(f"💾 Storyline saved to: {filepath}")
        return filepath

# --- TEST BLOCK ---
# You can run this file directly to test if Azure is working
if __name__ == "__main__":
    # Dummy data for testing
    test_stats = {
        'team_1': {'team_name': 'Mahomes Depot', 'score': 145.6},
        'team_2': {'team_name': 'Dak to the Future', 'score': 89.2}
    }
    
    print("🚀 Testing Azure Storyline Generator...")

    try:
        gen = StorylineGenerator()
        result = gen.generate_storyline(
            stats=test_stats,
            notable_performances=["Tyreek Hill: 35.2 pts", "Kyren Williams: 2 TDs"],
            storylines=["Mahomes Depot clinches playoffs"],
            records=["League high score for Week 12"]
        )
        
        if result:
            print("\n--- PREVIEW ---\n")
            print(result)
            # Optional: Test saving the file
            # gen.save_storyline(result, 12, "Test_Matchup")
            
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        print("💡 Hint: Check your .env file and ensure AZURE_OPENAI_API_KEY is set.")