from gensim.models import doc2vec
import os
import numpy as np
import random
from collections import Counter
import pandas as pd

dangerous_keywords = ['[', ']', '(', ')', '{', '}', '\'', '\"', ',',
                      '<', '>', '.', ';', ':', '\t', '\n']
filename = 'doc2vec_corpus'


def delete_empty():
    filelist = os.listdir('bugs_albums')
    for file_num in filelist:
        filepath = os.path.join('bugs_albums', file_num)
        with open(filepath, 'r') as f:
            contents = [lines for lines in f]
            total_string = ' '.join(contents).strip()
            if total_string == '':
                print('Removing empty file : {}'.format(file_num))
                os.remove(filepath)

def get_label(train_file_id, df):
    row = df.loc[df['index'] == int(train_file_id)]
    try:
        style = [row['스타일'].iloc[0].strip()]  # access the first row's value
    except (AttributeError, IndexError):
        style = []

    try:
        genre = [g.strip() for g in row['장르'].iloc[0].split('\\')]
    except (AttributeError, IndexError):
        genre = []
    return style + genre


def preprocess(line, train_file_name, df, replace_names=True):
    print('preprocessing : {}'.format(train_file_name))
    # delete keywords
    for keyword in dangerous_keywords:
        line = line.replace(keyword, ' ')

    if replace_names:
        # replace album name - choose the '앨범명' column and returns a Series
        album_name_series = df.loc[df['index'] == int(train_file_name)]['앨범명']
        try:
            album_name = str(album_name_series.iloc[0])  # access first row's value
        except IndexError:
            album_name = None

        if album_name != '' and album_name is not None:
            album_name_to_replace = ' [[{}]] '.format(train_file_name)
            line = line.replace(album_name, album_name_to_replace)

        # replace artist name
        artist_name_series = df.loc[df['index'] == int(train_file_name)]['아티스트']

        try:
            artist_name = str(artist_name_series.iloc[0])
        except IndexError:
            artist_name = None

        if artist_name != '' and artist_name is not None:
            artist_name_to_replace = ' (({})) '.format(train_file_name)
            line = line.replace(artist_name, artist_name_to_replace)
    return line


def create_tagged_doc_corpus():
    file_list = os.listdir('bugs_albums')
    num_files = len(file_list)

    train_files = np.random.permutation(file_list)
    print('The review files for train : {}'.format(num_files))

    # read album info file
    info_df = pd.read_csv('album_info.csv', index_col=False)

    with open(os.path.join('corpus', filename), 'w') as corpus_file:
        for trainfile in train_files:
            with open(os.path.join('bugs_albums', trainfile), 'r') as f:
                lines = f.readlines()
                # format : <trainfile> \t <preprocessed line> \n
                lines = ('{}\t{}\n'.format(trainfile, preprocess(l, trainfile, info_df)) for l in lines)
                corpus_file.writelines(lines)  # write to file


def read_data(tag_with_genres=True):
    # read in dataframe
    info_df = pd.read_csv('album_info.csv', index_col=False)

    with open(os.path.join('corpus', filename), 'r') as f:
        # list of [id, 'sentence blahblah']
        data = [line.strip().split('\t') for line in f]
    train_docs = []
    for row in data:
        try:
            id_num = int(row[0])
            split_words = row[1].split(' ')
            id_label = [id_num]

            # also add genre tags in training docs
            if tag_with_genres:
                id_label += get_label(id_num, info_df)

            # add the data
            train_docs.append((split_words, id_label))
        except IndexError:
            print('read_data() IndexError: {}'.format(row))
    tagged_train_docs = [doc2vec.TaggedDocument(words=doc, tags=tag) for doc, tag in train_docs]
    return tagged_train_docs

# delete empty files
# delete_empty()

# create doc corpus
# create_tagged_doc_corpus()

# read in data
print('Reading data')
tagged_train_docs = read_data()
print('length of train_docs : {}'.format(len(tagged_train_docs)))
print(tagged_train_docs[:2])  # sample doc

# train!
model = doc2vec.Doc2Vec(size=100, min_count=3)  # reduce dictionary size
print('Build vocab')
model.build_vocab(tagged_train_docs)
print('Train')
model.train(tagged_train_docs, total_examples=model.corpus_count, epochs=model.iter)

# save model
print('Model Saved')
model.save('models/doc2vec_2.0')

# load model
print('Loading Model')
model = doc2vec.Doc2Vec.load('models/doc2vec_2.0')
model.delete_temporary_training_data()  # save memory
model.init_sims(replace=True)
print('Model Loaded')
print('Dictionary size : {}'.format(model.corpus_count))
print('Estimated memory : {}'.format(model.estimate_memory()))
print('')


# test model
print('testing')
print(model.infer_vector(['크리스마스', '캐롤', '겨울']))

# test most similar
my_vec = model.infer_vector(['크리스마스', '캐롤', '겨울'])
# TODO: discard non-normalized syn0 and replace it with syn0norm.
print('most similar to 감성, 힙합')
similar_doc = model.docvecs.most_similar([my_vec], topn=10)
top_sim_idxs = [sim[0] for sim in similar_doc]
print(similar_doc)
print(top_sim_idxs)
print([rec.words for rec in tagged_train_docs if rec.tags[0] in top_sim_idxs])

# test with all documents in the training set
# ranks = []
# second_ranks = []
# for doc_id in range(len(tagged_train_docs)):
#     inferred_vector = model.infer_vector(tagged_train_docs[doc_id].words)
#     sims = model.docvecs.most_similar([inferred_vector],
#                                       topn=len(model.docvecs))
#     rank = [docid for docid, sim in sims].index(doc_id)
#     ranks.append(rank)
#
#     second_ranks.append(sims[1])
# print(Counter(ranks))  # Results vary due to random seeding and very small corpus

# Pick a random document from the test corpus and infer a vector from the model
# doc_id = random.randint(0, len(tagged_train_docs))

# Compare and print the most/median/least similar documents from the train corpus
# print('Train Document ({}): «{}»\n'.format(doc_id, ' '.join(tagged_train_docs[doc_id].words)))
sim_id = second_ranks[doc_id]
print('Similar Document {}: «{}»\n'.format(sim_id, ' '.join(tagged_train_docs[sim_id[0]].words)))
