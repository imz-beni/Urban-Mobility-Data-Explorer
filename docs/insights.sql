-- Insight 1: Trip demand by borough
SELECT b.borough_name,
       COUNT(*)        AS total_trips,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trips), 1)
                       AS pct_of_total
FROM   trips    t
JOIN   zones    z ON t.pu_zone_id  = z.zone_id
JOIN   boroughs b ON z.borough_id  = b.borough_id
GROUP  BY b.borough_name
ORDER  BY total_trips DESC;

-- Insight 2: Average fare per mile by time of day
SELECT time_of_day,
       ROUND(AVG(fare_per_mile), 2)  AS avg_fare_per_mile,
       ROUND(AVG(fare_amount), 2)    AS avg_fare,
       COUNT(*)                      AS trip_count
FROM   trips
WHERE  fare_per_mile > 0
  AND  fare_per_mile < 50
GROUP  BY time_of_day
ORDER  BY avg_fare_per_mile DESC;

-- Insight 3: Average speed by time of day (congestion)
SELECT time_of_day,
       ROUND(AVG(avg_speed_mph), 1)  AS avg_speed,
       ROUND(MIN(avg_speed_mph), 1)  AS min_speed,
       ROUND(MAX(avg_speed_mph), 1)  AS max_speed,
       COUNT(*)                      AS trip_count
FROM   trips
WHERE  avg_speed_mph BETWEEN 1 AND 60
GROUP  BY time_of_day
ORDER  BY avg_speed ASC;
