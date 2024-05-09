irc example

```bqrun SELECT refresh_date AS Day, term AS Top_Term, rank, FROM `bigquery-public-data.google_trends.top_terms\` WHERE refresh_date >= DATE_SUB(CURRENT_DATE(),INTERVAL 2 WEEK) AND rank = 1 GROUP BY Day, Top_Term, rank ORDER BY Day DESC```
should run

```bqrun SELECT * FROM `bigquery-public-data.google_trends.top_terms` WHERE rank > 0```
should not (2gb limit error)
