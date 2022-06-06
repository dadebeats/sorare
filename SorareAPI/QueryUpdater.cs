using System.Linq;

namespace SorareAPI
{
    public static class QueryUpdater
    {
        public static string AllCards(string nextCursor, string query)
        {

            if (nextCursor == null)
            {
                return query;
            }

            var InsertFilterAfterThis = "allCards (";
            var filterIndex = query.IndexOf(InsertFilterAfterThis) + InsertFilterAfterThis.Length; // TODO: vymyslet a upravit tak, aby to nebylo whitespace sensitive mezi allCards a (
            var filter = $"after:\"{nextCursor}\" ";
            query = query.Insert(filterIndex, filter);

            
            return query;
        }
    }
}
