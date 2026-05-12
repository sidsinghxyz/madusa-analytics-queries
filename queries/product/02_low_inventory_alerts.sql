-- File: queries/product/02_low_inventory_alerts.sql
-- Question: Variants at stock-out risk (stocked_quantity below threshold).
-- Dialect: postgres
-- Phase 3 coverage: bare WHERE — exercises filter_condition without enum.
-- Tables: inventory_levels, product_variants, stock_locations

SELECT sl.name        AS location,
       pv.sku,
       il.stocked_quantity,
       il.reserved_quantity
  FROM inventory_levels il
  JOIN product_variants pv ON pv.id = il.variant_id
  JOIN stock_locations sl  ON sl.id = il.location_id
 WHERE il.stocked_quantity < 50
   AND il.stocked_quantity > 0
 ORDER BY il.stocked_quantity ASC;
