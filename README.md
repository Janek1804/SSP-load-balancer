# HTTP(S) Resource-aware Load Balancer

## Źródła:
- ERA: Efficient Request Assignment
  Sterownik utrzymuje tablicę stanu serwerów (opóżnienie przetwarzania zapytań, wykorzystanie CPU i RAM, łączny czas odpowiedzi na zapytania)
  Przy otrzymaniu żądania sterownik najpierw odrzuca serwery, które nie mają wystarczających zasobów do obsługi żądania. Następnie na podstawie ważonej oceny uwzględniających opóźnienie i wykorzystanie zasobów przydziela zapytanie do najmniej obciążonego serwera.
- ABC: Artificial Bee Colony
  Sterownik dla każdego serwera przechowuje wskaźnik obciążenia (Liczba obsługiwanych zadań/zasoby). Na tej podstawie obliczana jest funkcja dostosowania: 1/(1+load)
  Zapytania są rozdzielane za pomocą selekcji ruletkowej na podstawie funkcji dostosowania  
