using System;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using GraphQL.Client.Serializer.Newtonsoft;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Client = GraphQL.Client.Http.GraphQLHttpClient;

namespace SorareAPI
{
    

    public class QueryProcessor
    {
        public static async Task<JObject> DownloadQueryData(string query, Client client, string variables)
        {
            //fetching data from queries

            var req = new GraphQL.GraphQLRequest
            {
                Variables = variables,
                Query = query
            };

            var response = await client.SendQueryAsync<object>(req);
            var data = (JObject) response.Data; // Newtonsoft.Json.Linq.JObject

            return data;
        }

        /**
        * Wrapper around DownloadQueryData.
        * Starts at firstCursor, gets the response, writes the data and passes the lastCursor seen as the newCursor.
        * Repeats until there is no nextPage. (end of data reached)
        * 
        */

        public static void DownloadAllPages(string firstCursor, string writePath, Client client, string query,
            string queryName)
        {

            var sw = new StreamWriter(writePath, append: true);
            var nextCursor = firstCursor;
            var hasNextPage = true;

            var timeoutCounter = 0;
            var apiCallsCount = 0;


            var serializer = new JsonSerializer();
            while (hasNextPage)
            {
                try
                {
                    var newVariables = "{" + $"\"cursor\": \"{nextCursor}\"" + "}";
                    var result = DownloadQueryData(query, client, newVariables).Result;
                    // TODO: procist dokumentaci JOBjectu a doladit performance wise- dvakrat pretypovavam na string
                    nextCursor = (string) result["allCards"]["pageInfo"]["endCursor"].ToString();
                    hasNextPage = (bool) result["allCards"]["pageInfo"]["hasNextPage"];
                    
                    
                    apiCallsCount++;
                    serializer.Serialize(sw, result);

                }
                catch(AggregateException)
                {
                    sw.Flush();
                    timeoutCounter++;
                    Console.WriteLine(nextCursor);
                    Console.WriteLine(apiCallsCount);
                    Console.WriteLine($"TIMEOUT BRASKO:{timeoutCounter}");
                    System.Threading.Thread.Sleep(60*1000);
                }
            }
            sw.Close();
        }

        public static void DownloadAllPlayersForAllClubs(string writePath, Client client, string query, JObject clubs)
        {
            
            var sw = new StreamWriter(writePath, append: false);
            sw.WriteLine("[");

            Console.WriteLine("Downloading all players for all clubs");
            var clubs_processed = 0;
            JObject data = null;
            foreach (var item in clubs["data"]["clubsReady"])
            {
                if (data != null)
                {
                    sw.WriteLine( data + ","); // write data with ',' only, when other data is coming
                }

                var teamSlug = item["slug"].ToString();
                var variables = "{" + $"\"teamSlug\": \"{teamSlug}\"" + "}";
                
                data = DownloadQueryData(query, client,variables).Result;
                clubs_processed++;
                Console.WriteLine("Clubs processed:" + clubs_processed);
            }
            sw.WriteLine(data); // last data, write without the ','
            sw.WriteLine("]");

            
            
            sw.Close();
            
        }
        

    }

}