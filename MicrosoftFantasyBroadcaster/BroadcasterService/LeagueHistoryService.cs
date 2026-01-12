using System.Text.Json;
using System.Text.Json.Serialization;

namespace BroadcasterService;

public class LeagueHistoryService
{
    private readonly string _filePath = "league_records.json";
    private LeagueRecords _records;

    public LeagueHistoryService()
    {
        if (File.Exists(_filePath))
        {
            string json = File.ReadAllText(_filePath);
            _records = JsonSerializer.Deserialize<LeagueRecords>(json) ?? new LeagueRecords();
        }
        else
        {
            _records = new LeagueRecords();
        }
    }

    // --- MAIN LOGIC: This matches your Python 'check_and_update_records' ---
    public string CheckForRecords(TeamStats teamStats, List<PlayerStats> roster)
    {
        var brokenRecords = new List<string>();
        string date = DateTime.Now.ToString("yyyy-MM-dd");

        // 1. TEAM SCORING RECORDS
        if (teamStats.Score > _records.HighestTeamScore.Value)
        {
            _records.HighestTeamScore = new RecordEntry { Value = teamStats.Score, Holder = teamStats.Name, Week = teamStats.Week, Date = date };
            brokenRecords.Add($"🏆 NEW RECORD! {teamStats.Name} scored {teamStats.Score} points - highest ever!");
        }

        if (teamStats.Score > 0 && teamStats.Score < _records.LowestTeamScore.Value)
        {
            _records.LowestTeamScore = new RecordEntry { Value = teamStats.Score, Holder = teamStats.Name, Week = teamStats.Week, Date = date };
            brokenRecords.Add($"😬 NEW LOW! {teamStats.Name} scored only {teamStats.Score} points.");
        }

        // 2. INDIVIDUAL PLAYER RECORDS
        foreach (var player in roster)
        {
            // Highest Individual Score
            if (player.Points > _records.HighestPlayerScore.Value)
            {
                _records.HighestPlayerScore = new RecordEntry { Value = player.Points, Holder = player.Name, Detail = player.Position, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                brokenRecords.Add($"🌟 NEW RECORD! {player.Name} ({player.Position}) scored {player.Points} points!");
            }

            // QB Records
            if (player.Position == "QB")
            {
                if (player.PassingYards > _records.MostPassingYards.Value)
                {
                    _records.MostPassingYards = new RecordEntry { Value = player.PassingYards, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                    brokenRecords.Add($"🚀 NEW RECORD! {player.Name} threw for {player.PassingYards} yards!");
                }
                if (player.PassingTDs > _records.MostPassingTDs.Value)
                {
                    _records.MostPassingTDs = new RecordEntry { Value = player.PassingTDs, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                    brokenRecords.Add($"🎯 NEW RECORD! {player.Name} threw {player.PassingTDs} TDs!");
                }
            }

            // RB Records
            if (player.Position == "RB")
            {
                if (player.RushingYards > _records.MostRushingYards.Value)
                {
                    _records.MostRushingYards = new RecordEntry { Value = player.RushingYards, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                    brokenRecords.Add($"🏃 NEW RECORD! {player.Name} rushed for {player.RushingYards} yards!");
                }
            }

            // WR/TE Records
            if (player.Position == "WR" || player.Position == "TE")
            {
                if (player.ReceivingYards > _records.MostReceivingYards.Value)
                {
                    _records.MostReceivingYards = new RecordEntry { Value = player.ReceivingYards, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                    brokenRecords.Add($"📡 NEW RECORD! {player.Name} had {player.ReceivingYards} receiving yards!");
                }
                if (player.Receptions > _records.MostReceptions.Value)
                {
                    _records.MostReceptions = new RecordEntry { Value = player.Receptions, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                    brokenRecords.Add($"🎣 NEW RECORD! {player.Name} caught {player.Receptions} passes!");
                }
            }

            // Total TDs (Any Position)
            if (player.TotalTDs > _records.MostTotalTDs.Value)
            {
                _records.MostTotalTDs = new RecordEntry { Value = player.TotalTDs, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                brokenRecords.Add($"🔥 NEW RECORD! {player.Name} scored {player.TotalTDs} TDs!");
            }

            // Defense Records
            if (player.Position == "D/ST")
            {
                if (player.Points > _records.MostDefensivePoints.Value)
                {
                    _records.MostDefensivePoints = new RecordEntry { Value = player.Points, Holder = player.Name, Team = teamStats.Name, Week = teamStats.Week, Date = date };
                    brokenRecords.Add($"🛡️ NEW RECORD! {player.Name} defense scored {player.Points} points!");
                }
            }
        }

        SaveChanges();
        return string.Join(" ", brokenRecords);
    }

    private void SaveChanges()
    {
        var options = new JsonSerializerOptions { WriteIndented = true };
        string json = JsonSerializer.Serialize(_records, options);
        File.WriteAllText(_filePath, json);
    }
}

// --- DATA STRUCTURES (The "Schema") ---

public class LeagueRecords
{
    public RecordEntry HighestTeamScore { get; set; } = new RecordEntry();
    public RecordEntry LowestTeamScore { get; set; } = new RecordEntry { Value = 999 }; // Start high

    public RecordEntry HighestPlayerScore { get; set; } = new RecordEntry();
    
    // QB
    public RecordEntry MostPassingYards { get; set; } = new RecordEntry();
    public RecordEntry MostPassingTDs { get; set; } = new RecordEntry();
    
    // RB
    public RecordEntry MostRushingYards { get; set; } = new RecordEntry();
    
    // WR/TE
    public RecordEntry MostReceivingYards { get; set; } = new RecordEntry();
    public RecordEntry MostReceptions { get; set; } = new RecordEntry();
    
    // General
    public RecordEntry MostTotalTDs { get; set; } = new RecordEntry();
    public RecordEntry MostDefensivePoints { get; set; } = new RecordEntry();
}

public class RecordEntry
{
    public double Value { get; set; } = 0; // Stores Yards, Score, or Count
    public string Holder { get; set; } = "None";
    public string Team { get; set; } = "";
    public string Detail { get; set; } = ""; // Extra info (like Position)
    public int Week { get; set; } = 0;
    public string Date { get; set; } = "";
}

// Helper classes to hold incoming data
public class TeamStats
{
    public string Name { get; set; } = "";
    public double Score { get; set; }
    public int Week { get; set; }
}

public class PlayerStats
{
    public string Name { get; set; } = "";
    public string Position { get; set; } = "";
    public double Points { get; set; }
    
    // Detailed Stats
    public double PassingYards { get; set; }
    public double PassingTDs { get; set; }
    public double RushingYards { get; set; }
    public double ReceivingYards { get; set; }
    public double Receptions { get; set; }
    public double TotalTDs { get; set; }
}