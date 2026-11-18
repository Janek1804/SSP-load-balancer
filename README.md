# HTTP(S) Resource-aware Load Balancer

## Źródła:
- ERA: Efficient Request Assignment
  Sterownik utrzymuje tablicę stanu serwerów (opóżnienie przetwarzania zapytań, wykorzystanie CPU i RAM, łączny czas odpowiedzi na zapytania)
  Przy otrzymaniu żądania sterownik najpierw odrzuca serwery, które nie mają wystarczających zasobów do obsługi żądania. Następnie na podstawie ważonej oceny uwzględniających opóźnienie i wykorzystanie zasobów przydziela zapytanie do najmniej obciążonego serwera.
- ABC: Artificial Bee Colony
  Sterownik dla każdego serwera przechowuje wskaźnik obciążenia (Liczba obsługiwanych zadań/zasoby). Na tej podstawie obliczana jest funkcja dostosowania: 1/(1+load)
  Zapytania są rozdzielane za pomocą selekcji ruletkowej na podstawie funkcji dostosowania  


## Topologia sieci

Sieć została zaprojektowana w oparciu o trójwarstwową architekturę hierarchiczną, składającą się z warstwy rdzeniowej (Core – S1), dystrybucyjnej (Distribution – S2, S3) oraz dostępowej (Access – S4, S5). Do przełącznika rdzeniowego podłączono dwóch klientów, natomiast cztery serwery komunikują się z siecią za pośrednictwem przełączników warstwy dostępowej. Poszczególne warstwy są połączone hierarchicznie, zapewniając uporządkowaną strukturę komunikacji w sieci.

![Topologia sieci](assets/network_topology.png)