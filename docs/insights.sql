-- insights.sql
-- Lancelot — Three SQL insight queries for the Urban Mobility Data Explorer
-- Each query answers a question about how NYC moves, using the normalized
-- schema (boroughs -> zones -> trips).

-- ============================================================
-- INSIGHT 1: Where do taxi trips start? (demand by borough)
-- ============================================================
-- Joins the trips fact table through the zones dimension to the
-- boroughs dimension, counting pickups per borough. This reveals
-- which boroughs generate the most taxi demand.

SELECT b.borough_name,
       COUNT(*)        AS total_trips,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trips), 1)
                       AS pct_of_total
FROM   trips    t
JOIN   zones    z ON t.pu_zone_id  = z.zone_id
JOIN   boroughs b ON z.borough_id  = b.borough_id
GROUP  BY b.borough_name
ORDER  BY total_trips DESC;

-- ============================================================
-- INSIGHT 2: Are rides pricier at certain times of day?
--            (average fare per mile by time-of-day bucket)
-- ============================================================
-- Filters out extreme fare_per_mile values (> $50/mile) that
-- represent data noise (very short trips with minimum fare).
-- Groups by Beni's derived time_of_day column to compare
-- pricing across morning, afternoon, evening, and night.

SELECT time_of_day,
       ROUND(AVG(fare_per_mile), 2)  AS avg_fare_per_mile,
       ROUND(AVG(fare_amount), 2)    AS avg_fare,
       COUNT(*)                      AS trip_count
FROM   trips
WHERE  fare_per_mile > 0
  AND  fare_per_mile < 50
GROUP  BY time_of_day
ORDER  BY avg_fare_per_mile DESC;

-- ============================================================
-- INSIGHT 3: When is the city slowest? (congestion by time of day)
-- ============================================================
-- Uses avg_speed_mph (derived feature: distance / duration) as
-- a proxy for traffic congestion. Filters out impossible speeds
-- (< 1 mph likely idle, > 60 mph likely highway/error).
-- Lower average speed = heavier congestion.

SELECT time_of_day,
       ROUND(AVG(avg_speed_mph), 1)  AS avg_speed,
       ROUND(MIN(avg_speed_mph), 1)  AS min_speed,
       ROUND(MAX(avg_speed_mph), 1)  AS max_speed,
       COUNT(*)                      AS trip_count
FROM   trips
WHERE  avg_speed_mph BETWEEN 1 AND 60
GROUP  BY time_of_day
ORDER  BY avg_speed ASC;
