# --------- Market Engine ---------
FROM microsoft/dotnet:2.2-runtime AS base
WORKDIR /app

FROM microsoft/dotnet:2.2-sdk AS build
WORKDIR /src
COPY MCSMarketEngine/MCSMarketEngine/MCSMarketEngine.csproj MCSMarketEngine/MCSMarketEngine/
COPY MCSLibrary/MCSLibrary/MCSLibrary.csproj MCSLibrary/MCSLibrary/
COPY MCSCowinLibrary/MCSCowinLibrary/MCSCowinLibrary.csproj MCSCowinLibrary/MCSCowinLibrary/
RUN dotnet restore MCSMarketEngine/MCSMarketEngine/MCSMarketEngine.csproj
COPY . .
WORKDIR /src/MCSMarketEngine
RUN dotnet build MCSMarketEngine/MCSMarketEngine.csproj -c Release -o /app

FROM build AS publish
RUN dotnet publish MCSMarketEngine/MCSMarketEngine.csproj -c Release -o /app

FROM base AS final
WORKDIR /app
COPY --from=publish /app .
ENTRYPOINT ["dotnet", "MCSMarketEngine.dll"]