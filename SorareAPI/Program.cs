using System.IO;
using Newtonsoft.Json.Linq;
using Newtonsoft.Json;
using Client = GraphQL.Client.Http.GraphQLHttpClient;
using Serializer = GraphQL.Client.Serializer.Newtonsoft.NewtonsoftJsonSerializer;


//TODO: Rozparsovat json na slugy hracu
//TODO: Protoze je pocet cards capplej na 50, tak budeme pouzivat posouvani se v kartach (after:cursor posledni karty), viz. gettingCardPricesFromSlug
namespace SorareAPI
{            
    //inspirace
    //https://github.com/sorare/api/issues/11

    class Program
    {
        public static void Main(string[] args)
        {

            const string apiUrl = @"https://api.sorare.com/graphql";
            var client = new Client(apiUrl, new Serializer());
            var key = File.ReadAllText("api_key.txt");
            var bearer = File.ReadAllText("bearer.txt");
            client.HttpClient.DefaultRequestHeaders.Add("JWT-AUD","sorare_plus");
            client.HttpClient.DefaultRequestHeaders.Add("Authorization", bearer);
            client.HttpClient.DefaultRequestHeaders.Add("APIKEY",key);
            
            var queryName = args[0];
            var queryPath = $"../../../queries/{queryName}.txt";
            var writePath = $"../../../../data/{queryName}.json";
            string query;
            using (var sr = new StreamReader(queryPath))
            {
                query = sr.ReadToEnd();
            }
            
            switch (queryName)
            {
                case "all_cards":
                    var firstCursor = "";
                    if (File.Exists("next_cursor.txt"))
                    {
                        firstCursor = File.ReadAllText("next_cursor.txt");
                    }
                    
                    // TODO:extend the method to work for all queries that use pagination
                    QueryProcessor.DownloadAllPages(firstCursor, writePath, client, query,queryName);
                    break;
                
                case "all_players":
                {
                    var clubs = JObject.Parse(File.ReadAllText("../../../../data/all_clubs.json"));
                    QueryProcessor.DownloadAllPlayersForAllClubs(writePath,client,query,clubs);
                    break;
                }
                // simple query that doesnt need many queries and modifications
                default:
                {
                    var sw = new StreamWriter(writePath, append: true);
                    sw.Write(QueryProcessor.DownloadQueryData(query, client,"").Result);
                    sw.Close();
                    break;
                }
            }






        }
    }
}