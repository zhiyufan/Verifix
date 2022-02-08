# Script to reproduce experiment

## Reproduce from existing result

```
python3 -m srcU.reproduce -m result -path_result ../result
```

## Reproduce Clara with single reference solution:

```
python3 -m srcU.reproduce -m clara -path_data ../data/itsp
```

## Reproduce Verifix with single reference solution:

```
python3 -m srcU.reproduce -m verifix -path_data ../data/itsp
```

## Reproduce Clara with multiple reference solutions:

```
python3 -m srcU.reproduce -m clara -path_data ../data/cluster
```

## Reproduce Verifix with multiple reference solutions:

```
python3 -m srcU.reproduce -m verifix -path_data ../data/cluster
```
