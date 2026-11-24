#include<stdio.h>
#include<stdlib.h>
#include<stdbool.h>
#include<string.h>

typedef struct linkedList{
	char* string;
	struct linkedList* next;
} linkedList;

#define MOVIE_GROUP_SEPERATOR ';'          //Seperates the movie groups
#define MOVIE_GROUP_NAME_SEPERATOR ':'     //Seperates the name of the group from the content of the group
#define MOVIE_NAME_SEPERATOR '@'           //Sperates between movie locations in a group
#define MOVIE_SHOW_SEPERATOR '#'           //Seperates the series location from specifc episode name
#define MOVIE_FILTER_SEPERATOR '\\'        //Seperates the filter char identifyer from its value, also starts the filter process ie name\id\filter, filter of type id is related to name

#define FILTER_STRING_SEPERATOR ';'        //Seperates the different filters in a continuous string
#define FILTER_MIN_MAX_SEPERATOR ':'       //Seperates the min max values within the continuous string

#define FILTER_STRING 's'                  //Filter type signifying the string pointer has data
#define FILTER_NUMBER_WITHIN 'm'           //Filter type signifying the min, and max values have data

typedef struct Filters{
	char target; //Which filter id to target
	char type; //Which type of filter this is
	char* string; //Filter string, used for mpaa classifications
	int min; //Filter min value, used for number in range requests
	int max; //Filter max value, other number for range requests
	struct Filters* next; //Linked list type pointing to the next filter
} Filters;

int stringToInt(char*);

Filters* parseFilterString(char* stringIn){
	char* s = calloc(strlen(stringIn)+1, sizeof(char));
	strcpy(s, stringIn);
	Filters* head = calloc(1, sizeof(Filters));
	Filters* tail = head;
	for (int i=0;s[i];i++){
		Filters* newNode = calloc(1, sizeof(Filters));
		newNode->target=s[i];
		newNode->type = s[i+1];
		tail->next = newNode;
		tail = newNode;
		if (newNode->type == FILTER_STRING){
			char* end = strchr(s+i, FILTER_STRING_SEPERATOR);
			end[0] = '\0';
			char* string = malloc(end - (s+i)-1);
			for (int j=0;s[j+i+2];j++){
				string[j] = s[i+j+2];
			}
			string[end-(s+i+2)] = 0; //Null byte
			newNode->string = string;
			i+= (end - (s+i));
			continue;
		}
		if (newNode->type == FILTER_NUMBER_WITHIN){
			char* second = strchr(s+i, FILTER_MIN_MAX_SEPERATOR);
			char* end = strchr(s+i, FILTER_STRING_SEPERATOR);
			*(second++) = 0;
			end[0] = 0;
			newNode->min = stringToInt(s+i);
			newNode->max = stringToInt(second);
			i+= (end - (s+i));
			continue;
		}
	}
	tail = head->next;
	free(head);
	free(s);
	return tail;
}

void freeFilters(Filters* f){
	Filters* next;
	while (f){
		next = f->next;
		free(f->string);
		free(f);
		f = next;
	}
}

char* getName(FILE* file, long offset, long size){
	long now = ftell(file);
	fseek(file, offset, SEEK_CUR);
	char* send = calloc(size+1, sizeof(char));
	fgets(send, size+1, file);
	fseek(file, now, SEEK_SET);
	send[size]=0;
	return send;
}

int stringToInt(char* string){
	int send = 0;
	for (int i=0;string[i];i++){
		if (string[i] < '0' || string[i] > '9') continue; //not a number, not handling negatives
		send = send*10 + (string[i] - '0');
	}
	return send;
}

linkedList* extractNames(FILE* file, size_t* entryCount, Filters* filters, linkedList** tailNode){
	int curr; //current char
	linkedList* head = calloc(1, sizeof(linkedList)); //to be sent back
	linkedList* currNode = head; //the current output string we're working on
	//After name portion
	for (curr=fgetc(file);curr != EOF && curr != MOVIE_GROUP_NAME_SEPERATOR;curr=fgetc(file)) { /*printf("File Parsing to name %c, %ld\n", curr, ftell(file));*/ continue; } //move to the : after the name
	if (curr == EOF) { printf("File parsing failed, didn't find the end of the name\n");fclose(file); return NULL; } //failed parsing
	//Now we are in the movie group
	char* nameOut;
	int nameSize=0;
	bool gotName = false;
	linkedList* newNode;
	*(entryCount) = 0;
	curr = fgetc(file); //Consume the : after
	for (;curr!=EOF;curr=fgetc(file)){
		if (curr == MOVIE_NAME_SEPERATOR || curr == MOVIE_GROUP_SEPERATOR){ //Got to the end of the current name
			if (!gotName && nameSize > 0){ //No filter info, so grab the name
				nameOut = getName(file, -nameSize-1, nameSize);
				newNode = calloc(1, sizeof(linkedList));
				newNode->string = nameOut;
				currNode->next = newNode;
				currNode = newNode;
				entryCount[0]++;
			}
			nameSize = 0;
			gotName = false;
			if (curr == MOVIE_GROUP_SEPERATOR) break;
			continue;
		}
		else if (curr == MOVIE_FILTER_SEPERATOR){
			//Go the the given filter values, and compare to our own
			//Filters are assumed to be in increasing order, so if its \a\c\b\ filter order, b will be dropped, or if \c\\b\\a\ then both b and a will be dropper regardless of their order
			Filters* currFilter = filters;
			long filterStart = ftell(file);
			bool moveOn = false;
			for (curr=fgetc(file);curr!=EOF;curr=fgetc(file)){
				if (curr == MOVIE_FILTER_SEPERATOR) continue;
				while (currFilter && currFilter->target != curr && !(curr==MOVIE_NAME_SEPERATOR || curr==MOVIE_GROUP_SEPERATOR)){ //Look for a filter we know that targets this filter name
					currFilter = currFilter->next;
				}
				if (!currFilter || curr == MOVIE_NAME_SEPERATOR || curr==MOVIE_GROUP_SEPERATOR){
					//Didn't find the remaining filter being looked for, get the name, it passed
					long reset = ftell(file);
					fseek(file, filterStart, SEEK_SET);
					nameOut = getName(file, -nameSize-1, nameSize);
					fseek(file, reset, SEEK_SET);
					newNode = calloc(1, sizeof(linkedList));
					newNode->string = nameOut;
					currNode->next = newNode;
					currNode = newNode;
					moveOn = true;
					entryCount[0]++;
					gotName = true;
					break;
				}
				//Now a correct filter has been found
				fgetc(file); //consume the \ before the data
				int size = 0;
				for (;curr != EOF && curr != MOVIE_FILTER_SEPERATOR && curr != MOVIE_NAME_SEPERATOR && curr != MOVIE_GROUP_SEPERATOR;curr=fgetc(file)) {size++;} //count the letters
				char* filterValue = getName(file, -size, size-1);
				fseek(file, -1, SEEK_CUR); //Unget the next operator
				if (currFilter->type == FILTER_STRING){
					//Supposed to be a string, compare values
					int diff = strcmp(currFilter->string, filterValue);
					if (diff == 0) { //Passed the filter, go to next target
						free(filterValue);
						continue;
					}
//NOTE - this here is resetting the file pointer and parsing it again and again, if performance continue being bad, rewrite to do comparisons and move ons in a loop here
					//Differ, see if there's another filter with this target
					char desiredTarget = currFilter->target;
					currFilter=currFilter->next;
					if (!currFilter || currFilter->target != desiredTarget) {moveOn = true; free(filterValue); break;} //Didn't find another filter with this target, it failed, move on
					fseek(file, -size-2+(curr==EOF?1:0), SEEK_CUR); //Move back to the start of the filter, continue on
					free(filterValue);
					continue;
				}
				if (currFilter->type == FILTER_NUMBER_WITHIN){
					//Supposed to be a range within
					int val = stringToInt(filterValue);
					if (val >= currFilter->min && val <= currFilter->max){ //Passed the range within, go to next target
						free(filterValue);
						continue;
					}
//NOTE - Same issues as above, but as of 7/30/2026, this is only used on single target filters, so the reset filter path will not be used. Unless it got changed, have fun
					char desiredTarget = currFilter->target;
					currFilter = currFilter->next;
					if (!currFilter || currFilter->target != desiredTarget) {moveOn = true; free(filterValue); break;} //Failed the filter, no more of this target, failed a filter group, move on
					fseek(file, -size-2, SEEK_CUR); //Move back to the start of the filter again
					free(filterValue);
					continue;
				}
				free(filterValue); //catch all, don't want memory leaks
			}
			if (moveOn){
//				printf("Failed filter of type %c, with string value of '%s'\n", currFilter?currFilter->type:'N', currFilter?currFilter->string:"NULL FILTER");
				for (;curr!=EOF && curr!=MOVIE_NAME_SEPERATOR && curr!=MOVIE_GROUP_SEPERATOR;curr=fgetc(file)){}
				if (curr == MOVIE_GROUP_SEPERATOR) { break; }
				nameSize=0;
				gotName = false;
			}
		}
		else{
			nameSize++;
		}
	}
	if (curr == EOF && !gotName && nameSize > 1){ //if we reached the end of the file without getting the name
		nameOut = getName(file, -nameSize, nameSize-1);
		newNode = calloc(1, sizeof(linkedList));
		newNode->string = nameOut;
		currNode->next = newNode;
		currNode = newNode;
		entryCount[0]++;
	}
	*tailNode = currNode;
	currNode = head->next;
	free(head);
	if (currNode && (void*)tailNode == (void*)currNode && strlen(currNode->string) == 0) return NULL; //If the filter catches the final name, werid bug, ad-hoc solution
	return currNode;
//TODO FIX!^^
}

char** extractData(char* filename, char* query, char* filterString, size_t* entryCount, bool exactMatch){
	//linkedList* extractNames(FILE* file, size_t* entryCount, Filters* filters, linkedList** tailNode){
	Filters* filters = parseFilterString(filterString);
	FILE* file = fopen(filename, "r");
	size_t queryIndex=0;
	size_t querySize = strlen(query);
	bool inName=true;
	int curr;
	char** send;
	linkedList* head = calloc(1, sizeof(linkedList));
	linkedList* currNode = head;
	size_t totalCount = 0;
	while((curr = fgetc(file)) != EOF){
		if (curr == ':') {
			inName=false;
			queryIndex=0;
			continue;
		}
		if (curr == ';') {
			inName=true;
			queryIndex=0;
			continue;
		}
		if (!inName) { continue; }
		//Now a normal character in the name section of the string
		if (curr != query[queryIndex] && (query[0] != '*' || querySize > 1)){ //if its incorrect and not a single star, reset
			queryIndex = 0;
			if (exactMatch) inName = false; //missed a mark, not exact match
			continue;
		}
		//curr == query @ queryIndex
		queryIndex++;
		if (queryIndex >= querySize){
			if (exactMatch){
				int next = fgetc(file);
				if (next == EOF) continue;
				if (next != ':'){ //more chars after inital match, we want exact
					inName=false; //tell program to skip until next name
					continue;
				}//if it reaches here, it will be an exact match, reverse by one to not screw up the name extraction
				fseek(file, -1, SEEK_CUR);
			}
			//Grab the name details from this data section
			size_t entries;
			linkedList* tail;
			linkedList* out = extractNames(file, &entries, filters, &tail);
			if (!out) {queryIndex=0; continue;} //No matches in the names, filtered out, reset and continue
			currNode->next = out;
			currNode = tail;
			totalCount += entries;
			queryIndex=0;
		}
	}
	fclose(file); //all done reading from the file
	*entryCount = totalCount;
	currNode = head->next;
	send = calloc(totalCount, sizeof(char*));
	totalCount=0; //will now track which index of send has been used
	if (!currNode) {free(head); return send;} //catch a no match case
	while(currNode){
		free(head);
		head = currNode;
		send[totalCount++] = currNode->string;
		currNode=currNode->next;
	}
	freeFilters(filters);
	free(head);
	return send;
}

char** extractRangedData(char* filename, size_t low, size_t high, char* filterString, size_t* entryCount){
	//Extracts results of those numeric values within the bounds inclusive, no negatives
	Filters* filters = parseFilterString(filterString);
	FILE* file = fopen(filename, "r");
	size_t currNum = 0; //the numerical value grabbed from the name section of data
	bool inName=true;
	int curr; //current char
	char** send;
	linkedList* head = calloc(1, sizeof(linkedList));
	linkedList* currNode = head;
	size_t totalCount = 0;
	while((curr = fgetc(file)) != EOF){
		if (curr == ':') {
			//reached the end, check if we're in bounds
			inName=false;
			if (currNum < low || currNum > high) { currNum=0; continue; } //out of specified bounds, skip
			//In Bounds
			size_t entries = 0;
			fseek(file, -1, SEEK_CUR);
			linkedList* tail;
			linkedList* out = extractNames(file, &entries, filters, &tail);
			if (!out) {currNum=0; inName=true; continue;} //No matches in the names, filtered out, reset and continue
			currNode->next = out;
			currNode = tail;
			totalCount += entries;
			currNum = 0; //reset
			inName = true;
			continue;
		}
		if (curr == ';') {
			inName=true;
			currNum=0; //reset
			continue;
		}
		if (!inName) { continue; }
		//Now a normal number in the name section of the string
		if (curr >= '0' && curr <= '9'){
			currNum = currNum * 10 + (curr-'0'); //5, '3' -> 53
		}
		if (curr == '*') currNum = high; //its a star, allow it to pass
		//Ignoring non-number characters
	}
	fclose(file); //all done reading from the file
	currNode = head->next;
	*entryCount = totalCount;
	send = calloc(totalCount, sizeof(char*));
	totalCount=0; //will now track which index of send has been used
	if (!currNode) {free(head); return send;} //catch a no match case
	while(currNode){
	free(head);
		head = currNode;
		send[totalCount++] = currNode->string;
		currNode=currNode->next;
	}
	freeFilters(filters);
	free(head);
	return send;
}

char** extractFilterData(char* filename, char** filterQueries, size_t filterSize, char* filterString, size_t* entryCount, bool exactMatch){
	//For results of many queries compiled into a single query from a file
	//Basically just does multiple queries of a file
	Filters* filters = parseFilterString(filterString);
	FILE* file = fopen(filename, "r");
	linkedList* head = calloc(1, sizeof(linkedList));
	linkedList* currNode = head; //effectively the tail argument
	size_t nameSize = 0;
	size_t totalCount =0;
	size_t* queryLengths = calloc(filterSize, sizeof(size_t));
	for (size_t i=0;i<filterSize;i++) { queryLengths[i] = strlen(filterQueries[i]); }
	bool inName = true;
	for (int curr = fgetc(file);curr != EOF;curr=fgetc(file)){
		if (curr == ':'){
			inName=false;
			char* name = getName(file, -nameSize-1, nameSize);
			bool match = false;
//TODO Add a star pass so all names will be matched for wildcard
			if (exactMatch){
				for (size_t i=0;i<filterSize;i++){
					int diff = strcmp(filterQueries[i], name);
					if (diff == 0){
						match = true;
						break;
					}
				}
			}
			else{
				size_t nameSize = strlen(name);
				//Try for partial match
				for (size_t i=0;i<filterSize;i++){ //i for each filter query
					if (nameSize < queryLengths[i]) { continue; } //if the query is too big for the name, move on
//					printf("Name: '%s', char: %c, target: '%s', strchr res: '%s', totalSize: %lu\n", name, filterQueries[i][0], filterQueries[i], strchr(name, filterQueries[i][0]), nameSize-queryLengths[i]);
					for (char* start=strchr(name, filterQueries[i][0]);start<name+nameSize-queryLengths[i]+1;start++){ //get the start position to start comparisons, relative to name
						if (start == NULL){match=false; break;}
//						printf("Start: '%s', %p\n", start, (void*)start);
						match=true;
						size_t k = (size_t)(start - name); //get the relative position in the name we are
						for (size_t j=0;j<queryLengths[i];j++){ //for j in the size of filterQueries[i]
//							printf("Name: '%s', Query: '%s', Name Char: %c, Query Cahr: %c, k: %lu, j: %lu\n", name, filterQueries[i], name[k+j], filterQueries[i][k+j], k, j);
							if (name[k+j] != filterQueries[i][j]) {match=false; break;}
						}
						if (match) break;
					}
					if (match) break;
				}
			}
//			printf("Match? %s\n", match?"true":"false");
			free(name);
			if (!match){
				continue; //No match, move on
			}
			fseek(file, -1, SEEK_CUR);
			size_t entries;
			linkedList* tail;
			linkedList* out = extractNames(file, &entries, filters, &tail);
			if (!out || !out->string) {nameSize=0; continue;} //No matches in the names, filtered out, reset and continue
			currNode->next = out;
			currNode = tail;
			totalCount += entries;
			inName = true;
			nameSize = 0;
			continue;
		}
		if (curr == ';'){
			inName = true;
			nameSize = 0;
			continue;
		}
		if (!inName) { continue; }
		nameSize++;
	}
	free(queryLengths);
	fclose(file);
	*entryCount = totalCount;
	currNode = head->next;
	char** send = calloc(totalCount, sizeof(char*));
	totalCount=0; //will now track which index of send has been used
	if (!currNode) {free(head); return send;} //catch a no match case
	while(currNode){
		free(head);
		head = currNode;
		send[totalCount++] = currNode->string;
		currNode=currNode->next;
	}
	free(head);
	freeFilters(filters);
	return send;
}

void freeArray(char** arr, size_t size){
	for (size_t i=0;i<size;i++){
		free(arr[i]);
	}
	free(arr);
}

int main(){
	size_t entryCount;
	char* filterString = "asnot rated;asg;aspg;aspg-13;asr;asx;bm0:100;cm0:10.0;dm0:1440;"; //"asg;aspg;aspg-13;asr;asx;bm0:100;cm0:100;dm0:120;";
	char** out = extractData("./test.mdr", "e", filterString, &entryCount, false);
	printf("Debug got a size of %lu:\n", entryCount);
	for (size_t i=0;i<entryCount;i++){
		printf("%s\n", out[i]);
		free(out[i]);
	}
	free(out);
	/*char** filterIn = calloc(2, sizeof(char*));
	filterIn[0]="smpeg4v3";
	filterIn[1]="non";
	out = extractFilterData("./test.mdr", filterIn, 2, filterString, &entryCount, false); //NOTE TO SELF - if not exact, (not in active use as writing), will not find exact match - obv bug, too lazy to fix, not using feature rn
	free(filterIn);
	printf("Filtered Debug got size of %lu:\n", entryCount);
	for (size_t i=0;i<entryCount;i++){
		printf("%s\n", out[i]);
		free(out[i]);
	}
	free(out);*/
/*	out = extractRangedData("./test.mdr", 100, 113, filterString, &entryCount);
	printf("Ranged Debug got size of %lu:\n", entryCount);
	for (size_t i=0;i<entryCount;i++){
		printf("%s, index: %ld\n", out[i], i);
		free(out[i]);
	}
	free(out);*/
	//FILE* f = fopen("./test.mdr", "r");
	//linkedList* extractNames(FILE* file, size_t* entryCount, Filters* filters, linkedList* tailNode)
	/*linkedList* tail;
	linkedList* out = extractNames(f, &entryCount, filters, &tail);
	printf("Got a count of: %lu\n", entryCount);
	while (out){
		tail = out->next;
		free(out->string);
		free(out);
		if (tail) printf("%s\n", tail->string);
		out = tail;
	}*/
	/*printf("Next char: %c\n", fgetc(f)); fseek(f, -1, SEEK_CUR);
	out = extractNames(f, &entryCount, filters, &tail);
	printf("Got a second count of: %lu\n", entryCount);
	while (out){
		tail = out->next;
		free(out->string);
		free(out);
		if (tail) printf("%s\n", tail->string);
		out = tail;
	}*/
	//freeFilters(filters);
	//fclose(f);
	return 0;
}
