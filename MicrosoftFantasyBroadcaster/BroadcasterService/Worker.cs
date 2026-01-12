using System.Text;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using Newtonsoft.Json.Linq;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.CognitiveServices.Speech;
using Microsoft.CognitiveServices.Speech.Audio;
using System.Text.RegularExpressions;

namespace BroadcasterService;

public class Worker : BackgroundService
{
    private readonly ILogger<Worker> _logger;
    private IConnection? _connection;
    private IChannel? _channel;
    private readonly string _queueName = "game_stats_queue";
    private readonly string _speechKey;
    private readonly string _speechRegion;

    public Worker(ILogger<Worker> logger)
    {
        _logger = logger;
        
        // Load Credentials
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_DEPLOYMENT_NAME") ?? "gpt-4";
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT");
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_KEY");
        
        _speechKey = Environment.GetEnvironmentVariable("SPEECH_KEY") ?? "";
        _speechRegion = Environment.GetEnvironmentVariable("SPEECH_REGION") ?? "westus2";

        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey) || string.IsNullOrEmpty(_speechKey))
        {
            _logger.LogError("❌ CRITICAL: Missing keys in launchSettings.json.");
            throw new InvalidOperationException("Missing Credentials");
        }
    }

    public override async Task StartAsync(CancellationToken cancellationToken)
    {
        var rabbitHost = Environment.GetEnvironmentVariable("RABBITMQ_HOST") ?? "localhost";
        var factory = new ConnectionFactory { HostName = rabbitHost };

        int attempts = 0;
        while (true)
        {
            try
            {
                _connection = await factory.CreateConnectionAsync();
                _channel = await _connection.CreateChannelAsync();
                await _channel.QueueDeclareAsync(queue: _queueName, durable: false, exclusive: false, autoDelete: false, arguments: null);
                _logger.LogInformation("✅ Connected to RabbitMQ. Waiting for Matt & Jose...");
                break;
            }
            catch
            {
                attempts++;
                if (attempts > 5) throw;
                _logger.LogWarning($"Waiting for RabbitMQ (Attempt {attempts})...");
                await Task.Delay(3000, cancellationToken);
            }
        }
        await base.StartAsync(cancellationToken);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (_channel == null) return;
        var consumer = new AsyncEventingBasicConsumer(_channel);

        consumer.ReceivedAsync += async (model, ea) =>
        {
            var body = ea.Body.ToArray();
            var message = Encoding.UTF8.GetString(body);

            try
            {
                var gameData = JObject.Parse(message);
                string shortName = gameData["shortName"]?.ToString() ?? "Recap";
                int week = (int)(gameData["week"] ?? 0);
                string? script = gameData["ai_recap"]?.ToString();

                _logger.LogInformation($"🤖 Processing Week {week} Script...");

                if (!string.IsNullOrEmpty(script))
                {
                    _logger.LogInformation("🎙️ Synthesizing Matt & Jose (Stock)...");
                    await GenerateVoiceAsync(script, shortName, week);
                }
                
                await _channel.BasicAckAsync(ea.DeliveryTag, false);
            }
            catch (Exception ex)
            {
                _logger.LogError($"❌ Error: {ex.Message}");
            }
        };

        await _channel.BasicConsumeAsync(queue: _queueName, autoAck: false, consumer: consumer);
        await Task.Delay(-1, stoppingToken);
    }

    private async Task GenerateVoiceAsync(string rawScript, string fileName, int week)
    {
        var speechConfig = SpeechConfig.FromSubscription(_speechKey, _speechRegion);
        
        // --- VOICE CONFIGURATION ---
        // Matt: Andrew (Professional Newscaster)
        // Jose: Davis (Stock Settings)
        string voiceMatt = "en-US-AndrewMultilingualNeural"; 
        string voiceJose = "en-US-DavisNeural";

        StringBuilder ssml = new StringBuilder();
        ssml.Append("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>");
        
        string[] lines = rawScript.Split(new[] { "\n" }, StringSplitOptions.RemoveEmptyEntries);

        foreach (var line in lines)
        {
            string cleanLine = line.Trim();
            if (string.IsNullOrEmpty(cleanLine)) continue;

            if (cleanLine.StartsWith("[MATT]:"))
            {
                string text = cleanLine.Replace("[MATT]:", "").Trim();
                // Matt = News Anchor style
                ssml.Append($"<voice name='{voiceMatt}'><mstts:express-as style='newscast'><mstts:silence type='Sentenceboundary' value='0ms'/>{text}</mstts:express-as></voice>");
            }
            else if (cleanLine.StartsWith("[JOSE]:"))
            {
                string text = cleanLine.Replace("[JOSE]:", "").Trim();
                // Jose (Davis) = Stock
                // Removed 'shouting', removed 'prosody' rate/pitch changes.
                // Kept 'silence' tag just to prevent robotic pauses between sentences.
                ssml.Append($"<voice name='{voiceJose}'><mstts:silence type='Sentenceboundary' value='0ms'/>{text}</voice>");
            }
            else
            {
                // Default to Matt
                ssml.Append($"<voice name='{voiceMatt}'><mstts:express-as style='newscast'>{cleanLine}</mstts:express-as></voice>");
            }
        }
        
        ssml.Append("</speak>");

        // Output File
        string baseFolder = Path.Combine(Directory.GetCurrentDirectory(), "Output");
        string weekFolder = Path.Combine(baseFolder, $"Week_{week}");
        if (!Directory.Exists(weekFolder)) Directory.CreateDirectory(weekFolder);
        string filePath = Path.Combine(weekFolder, $"{fileName}.wav");

        using var audioConfig = AudioConfig.FromWavFileOutput(filePath);
        using var synthesizer = new SpeechSynthesizer(speechConfig, audioConfig);
        
        var result = await synthesizer.SpeakSsmlAsync(ssml.ToString());

        if (result.Reason == ResultReason.SynthesizingAudioCompleted)
        {
            _logger.LogInformation($"✅ Multi-Speaker Audio saved: {filePath}");
        }
        else
        {
            _logger.LogError($"❌ Speech Error: {result.Reason}");
        }
    }
}