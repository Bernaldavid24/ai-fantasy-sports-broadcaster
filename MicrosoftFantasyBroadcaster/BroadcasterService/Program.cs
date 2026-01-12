using BroadcasterService;

// CRITICAL: Load the .env file from one directory up
DotNetEnv.Env.Load("../.env");

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddHostedService<Worker>();

var host = builder.Build();
host.Run();