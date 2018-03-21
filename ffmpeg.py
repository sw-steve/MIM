import uuid, os, time

class Ffmpeg:
    def __init__(self, config, folder, input_file):
        self.config=config
        self.options=config['encode_options']
        self.p1=config['p1_opts']
        self.p2=config['p2_opts']
        self.folder=folder
        self.input_file=input_file
        locuuid=str(uuid.uuid1())
        self.output_file=os.path.join(config['output_dir'], (locuuid + '.webm'))
        self.passlogfile=os.path.join(config['output_dir'], (locuuid + '.passlog'))
        self.pass_no=0
        
    def encode(self):
        #Pass 1
        self.pass_no=1
        print(self.commandgen(self.p1))
        #Temporary sleep to simulate encode
        time.sleep(5)

        #Pass 2
        self.pass_no=2
        print(self.commandgen(self.p2))
        #Temporary sleep to simulate encode
        time.sleep(5)

        #Done
        self.pass_no=3
        #Cleanup (Kill passlogs)

    #Takes the opts for first or second pass
    def commandgen(self, opts):
        #Add options to main options
        all_opts=self.options.copy()
        for i in opts.keys():
            all_opts[i]=opts[i]

        #Initial
        output='ffmpeg -i \"' + self.input_file + '\" -passlogfile ' + self.passlogfile + ' -threads ' + self.config['threads']

        #Add each argument
        for i in all_opts:
            output+=(' -' + i + ' ' + all_opts[i])

        #Add Output filename
        output+=' \"' + self.output_file + '\"'
        return output

