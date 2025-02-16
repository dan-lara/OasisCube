#include "DHT_Manager.h"

#define DHTPIN D4     // Broche de données du capteur DHT11
#define DHTTYPE DHT11 // Type de capteur DHT
// Création de l'instance du capteur DHT avec 5000ms d'interval
DHTManager dht(DHTPIN, DHTTYPE, 5000);

void setup() {
  delay(100);
  Serial.begin(115200);  // Initialisation de la communication série pour le débogage
  dht.begin();
}

void loop() {
  if (dht.update()) {
    // Si les données ont changé, les envoyer par MQTT
    Serial.print("Temperature: ");
    Serial.println(dht.getTemperature());
    Serial.print("Humidity: ");
    Serial.println(dht.getHumidity());
    // Exemple de publication MQTT
    String data = "<"+String(dht.getTemperature()) + ";" + String(dht.getHumidity())+">";
    Serial.println(data);
  }
  // delay(5000);
}