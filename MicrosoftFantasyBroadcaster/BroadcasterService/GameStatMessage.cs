using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace BroadcasterService
{
    public class GameStatMessage
    {
        // 'Week' is a value type (int), so it doesn't need a '?' unless you want it to be null.
        // Usually, 0 is fine for a default if missing.
        public int Week { get; set; }

        // Added '?' to make these nullable. 
        // This tells C#: "It's okay if this data is missing, don't crash."
        public string? ShortName { get; set; }

        [JsonPropertyName("home_team")]
        public string? HomeTeam { get; set; }

        [JsonPropertyName("home_score")]
        public double HomeScore { get; set; }

        [JsonPropertyName("home_roster")]
        public object? HomeRoster { get; set; }

        [JsonPropertyName("away_team")]
        public string? AwayTeam { get; set; }

        [JsonPropertyName("away_score")]
        public double AwayScore { get; set; }

        [JsonPropertyName("away_roster")]
        public object? AwayRoster { get; set; }

        [JsonPropertyName("storylines")]
        public List<string>? Storylines { get; set; }

        // This matches the Python "ai_recap" field
        [JsonPropertyName("ai_recap")]
        public string? AiRecap { get; set; }
    }
}