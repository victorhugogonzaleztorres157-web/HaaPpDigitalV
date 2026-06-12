from geopy.distance import geodesic

class TeleGeoAvanzado:
    def triangular(self, puntos):
        lat = sum(p['lat'] for p in puntos) / len(puntos)
        lon = sum(p['lon'] for p in puntos) / len(puntos)
        return {"lat": lat, "lon": lon}
