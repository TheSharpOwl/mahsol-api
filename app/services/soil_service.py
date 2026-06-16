import json
import os
import rasterio
import pyodbc
import logging
from collections import defaultdict
from app.core.config import settings

logger = logging.getLogger(__name__)

class SoilService:
    def __init__(self):
        self.mdb_path = settings.HWSD_MDB_PATH
        self.raster_path = settings.HWSD_RASTER_PATH
        
        # Determine ODBC driver based on environment
        if os.name == 'nt':  # Windows
            self.driver = "{Microsoft Access Driver (*.mdb, *.accdb)}"
        else:  # Linux (Docker)
            self.driver = "MDBTools"

    def _get_connection(self):
        conn_str = f"DRIVER={self.driver};DBQ={self.mdb_path};"
        return pyodbc.connect(conn_str)

    def get_smu_id(self, lat, lon):
        try:
            with rasterio.open(self.raster_path) as ds:
                coords = [(lon, lat)]  # (x=lon, y=lat)
                for value in ds.sample(coords):
                    return int(value[0])
        except Exception as e:
            logger.error(f"Error reading raster data: {e}")
            return None
        return None

    def get_soil_from_mdb(self, smu_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = f"SELECT * FROM HWSD2_LAYERS WHERE HWSD2_SMU_ID = {smu_id}"
                rows = cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error querying MDB: {e}")
            return []

    def filter_agriculture_layers(self, soil_layers):
        valid_layers = {"D1", "D2", "D3"}
        filtered = []
        for row in soil_layers:
            if row.get("LAYER") not in valid_layers:
                continue
            if row.get("SAND") == -7:
                continue
            filtered.append(row)
        return filtered

    def group_by_soil_type(self, soil_layers):
        grouped = defaultdict(list)
        for row in soil_layers:
            soil_type = row.get("WRB_PHASES")
            grouped[soil_type].append(row)
        return grouped

    def calculate_weighted_profile(self, grouped_soils):
        numeric_fields = [
            "SAND", "SILT", "CLAY", "PH_WATER", "ORG_CARBON",
            "CEC_SOIL", "BULK", "ELEC_COND", "GYPSUM", "AWC",
        ]
        totals = defaultdict(float)
        total_weight = 0
        soil_components = []

        for soil_type, layers in grouped_soils.items():
            if not layers: continue
            share = layers[0].get("SHARE", 0)
            depth_weights = {"D1": 0.5, "D2": 0.3, "D3": 0.2}
            
            soil_summary = {
                "soil_type": soil_type,
                "share_percent": share,
                "layers_used": [],
            }

            for layer in layers:
                layer_name = layer.get("LAYER")
                if layer_name not in depth_weights:
                    continue
                
                depth_weight = depth_weights[layer_name]
                final_weight = (share / 100) * depth_weight
                total_weight += final_weight
                soil_summary["layers_used"].append(layer_name)

                for field in numeric_fields:
                    value = layer.get(field)
                    if value is None or value == -7:
                        continue
                    totals[field] += value * final_weight
            
            soil_components.append(soil_summary)

        final_profile = {}
        for field in numeric_fields:
            if total_weight == 0:
                final_profile[field.lower()] = None
            else:
                final_profile[field.lower()] = round(totals[field] / total_weight, 2)

        return final_profile, soil_components

    def classify_texture(self, sand, clay):
        if sand is None or clay is None: return "Unknown"
        if clay >= 40: return "Clay"
        if sand >= 70: return "Sandy"
        if clay >= 27: return "Clay Loam"
        if sand >= 50: return "Sandy Loam"
        return "Loam"

    def get_agriculture_soil_profile(self, lat, lon):
        smu_id = self.get_smu_id(lat, lon)
        if not smu_id:
            return {"error": "No soil mapping unit found"}

        raw_soils = self.get_soil_from_mdb(smu_id)
        filtered_soils = self.filter_agriculture_layers(raw_soils)
        if not filtered_soils:
            return {"error": "No agriculture layers found for this SMU", "smu_id": smu_id}

        grouped_soils = self.group_by_soil_type(filtered_soils)
        weighted_profile, soil_components = self.calculate_weighted_profile(grouped_soils)
        
        texture = self.classify_texture(
            weighted_profile.get("sand"), 
            weighted_profile.get("clay")
        )

        return {
            "smu_id": smu_id,
            "soil_texture": texture,
            "profile": weighted_profile,
            "components": soil_components
        }

soil_service = SoilService()
