# Example use
# IP_ADDRESS=192.168.28.253 make test1
all: test1 test2

test1: test.c
	$(CC) -DTEST1 -Os -W -Wall -Werror -o build/test1 test.c && \
		if [ `hostname` = "debugger" ]; then sshpass -f ~/pwd scp build/$@ $(IP_ADDRESS):~/Desktop/; fi

test2: test.c
	$(CC) -DTEST2 -Os -W -Wall -Werror -o build/test2 test.c && \
		if [ `hostname` = "debugger" ]; then sshpass -f ~/pwd scp build/$@ $(IP_ADDRESS):~/Desktop/; fi

clean:
	rm -Rf build/*
